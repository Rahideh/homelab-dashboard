// ===== تنظیمات =====
const POLL_INTERVAL_MS = 30000; // هر ۳۰ ثانیه رفرش خودکار

const DEVICE_TYPE_LABELS = {
  mikrotik: "MikroTik",
  cisco: "Cisco",
  hpe_server: "HPE Server",
  other: "دستگاه دیگر",
};

const ALERT_TYPE_LABELS = {
  high_temp: "دمای بالا",
  offline: "آفلاین شد",
  online: "آنلاین شد",
  new_device: "دستگاه جدید",
};

let deviceChart = null;
let trafficChart = null;

// ===== توابع کمکی فرمت‌بندی =====

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, i);
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatUptime(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}روز ${hours}ساعت`;
  if (hours > 0) return `${hours}ساعت ${minutes}دقیقه`;
  return `${minutes}دقیقه`;
}

function formatLastSeen(seconds) {
  if (seconds === null || seconds === undefined) return "بدون داده";
  if (seconds < 15) return "همین الان";
  if (seconds < 60) return `${seconds} ثانیه پیش`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} دقیقه پیش`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} ساعت پیش`;
  return `${Math.floor(seconds / 86400)} روز پیش`;
}

function formatRelativeTime(isoLikeString) {
  // recorded_at از بک‌اند به‌صورت UTC میاد بدون ذکر صریح timezone،
  // پس اینجا هم صریحاً به‌عنوان UTC پارسش می‌کنیم (مشابه فیکسی که تو api_devices.php زدیم)
  const utcString = isoLikeString.replace(" ", "T") + "Z";
  const date = new Date(utcString);
  return date.toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" });
}

// ===== دریافت داده از بک‌اند =====

async function fetchDevices() {
  const res = await fetch(`${API_BASE}/api_devices.php`, { cache: "no-store" });
  if (!res.ok) throw new Error(`api_devices.php: HTTP ${res.status}`);
  const data = await res.json();
  return data.devices || [];
}

async function fetchAlerts(limit = 15) {
  const res = await fetch(`${API_BASE}/api_alerts.php?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`api_alerts.php: HTTP ${res.status}`);
  const data = await res.json();
  return data.alerts || [];
}

async function fetchHistory(deviceId, limit = 50) {
  const res = await fetch(`${API_BASE}/api_history.php?device_id=${deviceId}&limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`api_history.php: HTTP ${res.status}`);
  const data = await res.json();
  return data.history || [];
}

// ===== رندر کارت‌های خلاصه =====

function renderSummary(devices) {
  const onlineCount = devices.filter((d) => d.is_online).length;
  const offlineCount = devices.length - onlineCount;
  const warningCount = devices.filter(
    (d) => d.last_metric && d.last_metric.temperature_c !== null &&
           d.last_metric.temperature_c >= d.temp_warning_threshold
  ).length;

  const el = document.getElementById("summary-row");
  el.innerHTML = `
    <div class="summary-card">
      <div class="label">کل دستگاه‌ها</div>
      <div class="value">${devices.length}</div>
    </div>
    <div class="summary-card">
      <div class="label">آنلاین</div>
      <div class="value green">${onlineCount}</div>
    </div>
    <div class="summary-card">
      <div class="label">آفلاین</div>
      <div class="value ${offlineCount > 0 ? "red" : ""}">${offlineCount}</div>
    </div>
    <div class="summary-card">
      <div class="label">هشدار دما</div>
      <div class="value ${warningCount > 0 ? "orange" : ""}">${warningCount}</div>
    </div>
  `;
}

// ===== رندر کارت‌های دستگاه =====

function renderDeviceCard(device) {
  const m = device.last_metric;
  const isTempWarning = m && m.temperature_c !== null && m.temperature_c >= device.temp_warning_threshold;

  const cardClasses = ["device-card"];
  if (!device.is_online) cardClasses.push("offline");
  else if (isTempWarning) cardClasses.push("temp-warning");

  const cpuDisplay = m && m.cpu_percent !== null
    ? `<div class="metric"><div class="metric-label">CPU</div><div class="metric-value">${m.cpu_percent.toFixed(1)}%</div></div>`
    : `<div class="metric"><div class="metric-label">CPU</div><div class="metric-value na">در دسترس نیست</div></div>`;

  const tempDisplay = m && m.temperature_c !== null
    ? `<div class="metric"><div class="metric-label">دما</div><div class="metric-value ${isTempWarning ? "warning" : ""}">${m.temperature_c.toFixed(1)}°C</div></div>`
    : `<div class="metric"><div class="metric-label">دما</div><div class="metric-value na">در دسترس نیست</div></div>`;

  const uptimeDisplay = m && m.uptime_seconds !== null
    ? `<div class="metric"><div class="metric-label">Uptime</div><div class="metric-value" style="font-size:13px">${formatUptime(m.uptime_seconds)}</div></div>`
    : "";

  const trafficDisplay = m && m.traffic_rx_bytes !== null
    ? `<div class="metric"><div class="metric-label">ترافیک (RX/TX)</div><div class="metric-value" style="font-size:12px">${formatBytes(m.traffic_rx_bytes)} / ${formatBytes(m.traffic_tx_bytes)}</div></div>`
    : "";

  const typeLabel = DEVICE_TYPE_LABELS[device.device_type] || device.device_type;

  const div = document.createElement("div");
  div.className = cardClasses.join(" ");
  div.dataset.deviceId = device.id;
  div.dataset.deviceName = device.display_name;
  div.innerHTML = `
    <div class="device-card-header">
      <div>
        <div class="device-name">${device.display_name}</div>
        <span class="device-type-badge">${typeLabel}</span>
      </div>
      <span class="status-pill ${device.is_online ? "online" : "offline"}">
        ${device.is_online ? "آنلاین" : "آفلاین"}
      </span>
    </div>
    <div class="metrics-row">
      ${cpuDisplay}
      ${tempDisplay}
      ${uptimeDisplay}
      ${trafficDisplay}
    </div>
    <div class="device-footer">
      آخرین بروزرسانی: ${formatLastSeen(device.seconds_since_last_seen)}
    </div>
  `;
  div.addEventListener("click", () => openDeviceModal(device.id, device.display_name));
  return div;
}

function renderDevices(devices) {
  const grid = document.getElementById("device-grid");
  if (devices.length === 0) {
    grid.innerHTML = `<div class="empty-state">هنوز هیچ دستگاهی داده‌ای نفرستاده. Agent ها رو اجرا کن.</div>`;
    return;
  }
  grid.innerHTML = "";
  devices.forEach((device) => grid.appendChild(renderDeviceCard(device)));
}

// ===== رندر لاگ هشدارها =====

function renderAlerts(alerts) {
  const panel = document.getElementById("alerts-panel");
  if (alerts.length === 0) {
    panel.innerHTML = `<div class="empty-state">هنوز هشداری ثبت نشده.</div>`;
    return;
  }
  panel.innerHTML = alerts.map((alert) => {
    const badgeClass = ALERT_TYPE_LABELS[alert.alert_type] ? alert.alert_type : "other";
    const label = ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type;
    return `
      <div class="alert-row">
        <div class="alert-left">
          <span class="alert-badge ${badgeClass}">${label}</span>
          <span>${alert.display_name}</span>
        </div>
        <span class="alert-time">${formatRelativeTime(alert.created_at)}</span>
      </div>
    `;
  }).join("");
}

// ===== مودال جزئیات + گراف =====

async function openDeviceModal(deviceId, displayName) {
  document.getElementById("modal-title").textContent = displayName;
  document.getElementById("modal-overlay").classList.add("active");

  try {
    const history = await fetchHistory(deviceId, 50);
    renderCharts(history);
  } catch (e) {
    console.error("خطا در دریافت تاریخچه:", e);
  }
}

function closeModal() {
  document.getElementById("modal-overlay").classList.remove("active");
}

function renderCharts(history) {
  const labels = history.map((h) => formatRelativeTime(h.recorded_at));
  const cpuData = history.map((h) => h.cpu_percent);
  const tempData = history.map((h) => h.temperature_c);
  const rxData = history.map((h) => h.traffic_rx_bytes);
  const txData = history.map((h) => h.traffic_tx_bytes);

  const ctx1 = document.getElementById("cpu-temp-chart").getContext("2d");
  if (deviceChart) deviceChart.destroy();
  deviceChart = new Chart(ctx1, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "CPU %",
          data: cpuData,
          borderColor: "#4ea1ff",
          backgroundColor: "rgba(78,161,255,0.1)",
          tension: 0.3,
          spanGaps: true,
        },
        {
          label: "دما (°C)",
          data: tempData,
          borderColor: "#fbbf24",
          backgroundColor: "rgba(251,191,36,0.1)",
          tension: 0.3,
          spanGaps: true,
        },
      ],
    },
    options: chartOptions("CPU / دما"),
  });

  const ctx2 = document.getElementById("traffic-chart").getContext("2d");
  if (trafficChart) trafficChart.destroy();
  trafficChart = new Chart(ctx2, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "دریافتی (RX)",
          data: rxData,
          borderColor: "#34d399",
          backgroundColor: "rgba(52,211,153,0.1)",
          tension: 0.3,
          spanGaps: true,
        },
        {
          label: "ارسالی (TX)",
          data: txData,
          borderColor: "#f87171",
          backgroundColor: "rgba(248,113,113,0.1)",
          tension: 0.3,
          spanGaps: true,
        },
      ],
    },
    options: chartOptions("ترافیک (بایت)"),
  });
}

function chartOptions(title) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: { display: true, text: title, color: "#dbe4f5" },
      legend: { labels: { color: "#dbe4f5" } },
    },
    scales: {
      x: { ticks: { color: "#7c8bab" }, grid: { color: "#1a2540" } },
      y: { ticks: { color: "#7c8bab" }, grid: { color: "#1a2540" } },
    },
  };
}

// ===== حلقه‌ی اصلی رفرش =====

async function refreshDashboard() {
  const statusEl = document.getElementById("topbar-status");
  try {
    const [devices, alerts] = await Promise.all([fetchDevices(), fetchAlerts()]);
    renderSummary(devices);
    renderDevices(devices);
    renderAlerts(alerts);
    statusEl.textContent = `آخرین بروزرسانی: ${new Date().toLocaleTimeString("fa-IR")}`;
  } catch (e) {
    console.error(e);
    statusEl.textContent = "خطا در اتصال به بک‌اند — کنسول مرورگر رو چک کن";
  }
}

document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-overlay").addEventListener("click", (e) => {
  if (e.target.id === "modal-overlay") closeModal();
});

refreshDashboard();
setInterval(refreshDashboard, POLL_INTERVAL_MS);
