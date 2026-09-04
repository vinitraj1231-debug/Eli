/* ===================== GLOBALS ===================== */
const API = '';
let currentUser = null;
let currentDepId = null;
let logPolling = null;

/* ===================== TOAST ===================== */
function toast(msg, type = 'info') {
    const c = document.querySelector('.toast-container') || createToastContainer();
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>${msg}`;
    c.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(40px)'; setTimeout(() => t.remove(), 300); }, 3500);
}
function createToastContainer() {
    const c = document.createElement('div'); c.className = 'toast-container';
    document.body.appendChild(c); return c;
}

/* ===================== API HELPER ===================== */
async function api(url, options = {}) {
    const res = await fetch(API + url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Request failed', 'error'); throw new Error(data.error); }
    return data;
}

/* ===================== INTERACTIVE LANDING PAGE FEATURES ===================== */
let currentBillingCycle = 'monthly'; // 'monthly' or 'yearly'

function toggleBillingCycle() {
    const knob = document.getElementById('toggle-knob');
    const labelMonthly = document.getElementById('label-monthly');
    const labelYearly = document.getElementById('label-yearly');

    const priceShared = document.getElementById('price-shared');
    const priceVps = document.getElementById('price-vps');
    const priceDedicated = document.getElementById('price-dedicated');

    const cycleShared = document.getElementById('cycle-shared');
    const cycleVps = document.getElementById('cycle-vps');
    const cycleDedicated = document.getElementById('cycle-dedicated');

    if (currentBillingCycle === 'monthly') {
        currentBillingCycle = 'yearly';
        knob.classList.replace('translate-x-0', 'translate-x-6');
        labelMonthly.classList.replace('text-white', 'text-slate-400');
        labelYearly.classList.replace('text-slate-400', 'text-white');

        // Apply 20% savings: 99 -> 79, 199 -> 159, 299 -> 239
        priceShared.textContent = '₹79';
        priceVps.textContent = '₹159';
        priceDedicated.textContent = '₹239';

        cycleShared.textContent = '/month (billed yearly)';
        cycleVps.textContent = '/month (billed yearly)';
        cycleDedicated.textContent = '/month (billed yearly)';
    } else {
        currentBillingCycle = 'monthly';
        knob.classList.replace('translate-x-6', 'translate-x-0');
        labelMonthly.classList.replace('text-slate-400', 'text-white');
        labelYearly.classList.replace('text-white', 'text-slate-400');

        priceShared.textContent = '₹99';
        priceVps.textContent = '₹199';
        priceDedicated.textContent = '₹299';

        cycleShared.textContent = '/month';
        cycleVps.textContent = '/month';
        cycleDedicated.textContent = '/month';
    }
}

// Simulated build & deployment check
function simulateDeploymentCheck(event) {
    event.preventDefault();
    const input = document.getElementById('buildSimInput').value.trim();
    const runtime = document.getElementById('buildSimRuntime').value;
    const resultBox = document.getElementById('buildSimResult');

    if (!input) return;

    const cleanName = input.replace(/^(https?:\/\/)?(github\.com\/)?/, '').replace(/\.git$/, '');

    resultBox.classList.remove('hidden');
    resultBox.innerHTML = `
        <div class="flex items-center gap-2">
            <span class="spinner"></span>
            <span class="text-slate-400 font-mono">Running build diagnostic simulation for ${cleanName} (${runtime})...</span>
        </div>
    `;

    setTimeout(() => {
        resultBox.innerHTML = `
            <div class="flex flex-col gap-2 w-full text-left">
                <div class="flex justify-between items-center">
                    <span class="font-bold text-emerald-400 font-mono">⚡ Build Nominal & Fully Compatible!</span>
                    <a href="/register" class="bg-cyberPrimary hover:bg-cyberAccent text-cyberBg font-heading font-bold text-[10px] px-3 py-1 rounded-md uppercase transition-all shadow-neonCyan">Deploy Now</a>
                </div>
                <div class="text-[11px] font-mono text-slate-400 bg-cyberDark/80 p-2.5 rounded border border-cyberBorder space-y-1">
                    <div class="text-cyberPrimary font-semibold">[SIMULATION DIAGNOSTICS]</div>
                    <div>> Target Environment: ${runtime} Container Namespace</div>
                    <div>> Resolving package manifest dependencies... Done</div>
                    <div>> Encrypted secret vault env injection ready.</div>
                    <div>> Estimated boot execution time: &lt; 2.1s</div>
                </div>
            </div>
        `;
        resultBox.className = "mt-3 p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-xs flex justify-between items-center";
    }, 1200);
}

// Instant Latency diagnostic tester
function triggerLatencyTest() {
    const status = document.getElementById('status-latency');
    status.textContent = 'Diagnostics Running...';
    status.className = 'text-cyberPrimary animate-pulse';

    const pings = {
        mumbai: document.getElementById('ping-mumbai'),
        delhi: document.getElementById('ping-delhi'),
        singapore: document.getElementById('ping-singapore'),
        frankfurt: document.getElementById('ping-frankfurt')
    };

    // Mumbai: 8-15ms, Delhi: 15-28ms, Singapore: 35-50ms, Frankfurt: 95-120ms
    const simulatePing = (el, min, max) => {
        el.textContent = 'pinging...';
        el.className = 'font-mono text-slate-400';
        setTimeout(() => {
            const val = Math.floor(Math.random() * (max - min + 1)) + min;
            el.textContent = `${val} ms`;
            el.className = 'font-mono text-emerald-400 font-bold';
        }, Math.random() * 800 + 400);
    };

    simulatePing(pings.mumbai, 8, 15);
    simulatePing(pings.delhi, 15, 28);
    simulatePing(pings.singapore, 35, 52);
    simulatePing(pings.frankfurt, 92, 118);

    setTimeout(() => {
        status.textContent = 'All Nodes Nominal';
        status.className = 'text-emerald-400 font-bold';
    }, 1400);
}

// Global server mock dashboard visual loop updates
function initMockMetricsVisual() {
    const cpu = document.getElementById('dash-cpu');
    const ram = document.getElementById('dash-ram');
    const net = document.getElementById('dash-net');

    const cpuBar = document.getElementById('dash-cpu-bar');
    const ramBar = document.getElementById('dash-ram-bar');
    const netBar = document.getElementById('dash-net-bar');

    if (!cpu || !ram || !net) return;

    setInterval(() => {
        // CPU: fluctuate 12% - 48%
        const cpuVal = (Math.random() * 36 + 12).toFixed(1);
        cpu.textContent = `${cpuVal}%`;
        cpuBar.style.width = `${cpuVal}%`;

        // RAM: fluctuate 390MB - 620MB (on max 1024MB VPS scale)
        const ramVal = Math.floor(Math.random() * 230 + 390);
        ram.textContent = `${ramVal} MB`;
        ramBar.style.width = `${(ramVal / 1024 * 100).toFixed(0)}%`;

        // Network: fluctuate 6.8 - 9.8 Gbps
        const netVal = (Math.random() * 3.0 + 6.8).toFixed(1);
        net.textContent = `${netVal} Gbps`;
        netBar.style.width = `${(netVal / 10 * 100).toFixed(0)}%`;

    }, 3000);
}

/* ===================== LANDING PAGE ===================== */
function initLanding() {
    // Scroll reveal (using intersection observer)
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(e => { if (e.isIntersecting) { e.target.style.opacity = '1'; e.target.style.transform = 'translateY(0)'; } });
    }, { threshold: 0.1 });
    document.querySelectorAll('.reveal').forEach(el => {
        el.style.opacity = '0'; el.style.transform = 'translateY(20px)';
        el.style.transition = 'all 0.6s ease-out'; observer.observe(el);
    });

    // Constellation Interactive 3D/CSS Canvas Constellation matrix background
    (function() {
        const canvas = document.getElementById('canvas3d');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let width = canvas.width = canvas.offsetWidth;
        let height = canvas.height = canvas.offsetHeight;

        const particles = [];
        const maxParticles = 65;
        const connectionDist = 130;

        class Particle {
            constructor() {
                this.x = Math.random() * width;
                this.y = Math.random() * height;
                this.vx = (Math.random() - 0.5) * 0.5;
                this.vy = (Math.random() - 0.5) * 0.5;
                this.radius = Math.random() * 1.8 + 1;
            }
            update() {
                this.x += this.vx;
                this.y += this.vy;
                if (this.x < 0 || this.x > width) this.vx *= -1;
                if (this.y < 0 || this.y > height) this.vy *= -1;
            }
            draw() {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(0, 242, 254, 0.65)';
                ctx.shadowBlur = 6;
                ctx.shadowColor = '#00f2fe';
                ctx.fill();
                ctx.shadowBlur = 0; // reset
            }
        }

        for (let i = 0; i < maxParticles; i++) {
            particles.push(new Particle());
        }

        function drawLines() {
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const p1 = particles[i];
                    const p2 = particles[j];
                    const dist = Math.hypot(p1.x - p2.x, p1.y - p2.y);
                    if (dist < connectionDist) {
                        const alpha = (1 - dist / connectionDist) * 0.12;
                        ctx.strokeStyle = `rgba(0, 242, 254, ${alpha})`;
                        ctx.lineWidth = 0.7;
                        ctx.beginPath();
                        ctx.moveTo(p1.x, p1.y);
                        ctx.lineTo(p2.x, p2.y);
                        ctx.stroke();
                    }
                }
            }
        }

        function animate() {
            ctx.clearRect(0, 0, width, height);
            particles.forEach(p => {
                p.update();
                p.draw();
            });
            drawLines();
            requestAnimationFrame(animate);
        }

        window.addEventListener('resize', () => {
            if (!canvas) return;
            width = canvas.width = canvas.offsetWidth;
            height = canvas.height = canvas.offsetHeight;
        });

        animate();
    })();

    // Run diagnostics immediately
    triggerLatencyTest();
    // Run metrics daemon
    initMockMetricsVisual();
}

/* ===================== AUTH PAGE ===================== */
function initAuth() {
    const mode = document.body.dataset.mode;
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = loginForm.querySelector('button[type="submit"]');
            btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
            try {
                const data = await api('/api/auth/login', {
                    method: 'POST',
                    body: JSON.stringify({
                        username: document.getElementById('loginUser').value,
                        password: document.getElementById('loginPass').value
                    })
                });
                toast('Login successful', 'success');
                setTimeout(() => window.location.href = '/dashboard', 500);
            } catch (err) { btn.disabled = false; btn.textContent = 'Login'; }
        });
    }

    if (registerForm) {
        const refField = document.getElementById('regRef');
        if (refField && window.location.search.includes('ref=')) {
            const params = new URLSearchParams(window.location.search);
            refField.value = params.get('ref') || '';
        }
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = registerForm.querySelector('button[type="submit"]');
            btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
            try {
                const data = await api('/api/auth/register', {
                    method: 'POST',
                    body: JSON.stringify({
                        username: document.getElementById('regUser').value,
                        email: document.getElementById('regEmail').value,
                        password: document.getElementById('regPass').value,
                        referral: document.getElementById('regRef').value
                    })
                });
                toast('Account created!', 'success');
                setTimeout(() => window.location.href = '/dashboard', 500);
            } catch (err) { btn.disabled = false; btn.textContent = 'Create Account'; }
        });
    }
}

/* ===================== DASHBOARD ===================== */
function initDashboard() {
    loadUser();
    switchTab('home');

    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
}

function switchTab(tab) {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    document.querySelector(`.nav-item[data-tab="${tab}"]`)?.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    const panel = document.getElementById(`tab-${tab}`);
    if (panel) panel.classList.remove('hidden');

    if (logPolling) { clearInterval(logPolling); logPolling = null; }

    switch (tab) {
        case 'home': loadStats(); break;
        case 'manage': loadDeployments(); break;
        case 'deploy': initDeployForm(); break;
        case 'settings': loadSettings(); break;
    }
}

async function loadUser() {
    try {
        currentUser = await api('/api/auth/me');
        const avatar = document.querySelector('.dash-user-avatar');
        const name = document.querySelectorAll('.dash-user-name');
        if (avatar) avatar.textContent = currentUser.username[0].toUpperCase();
        name.forEach(el => { el.textContent = currentUser.username; });
    } catch { window.location.href = '/login'; }
}

async function loadStats() {
    try {
        const s = await api('/api/dashboard/stats');
        document.getElementById('statTotal').textContent = s.total_deployments;
        document.getElementById('statCredits').textContent = s.credits;
        document.getElementById('statWallet').textContent = '₹' + s.wallet.toFixed(2);

        if (s.free_deploy_until) {
            updateTimer(s.free_deploy_until);
            if (!window.timerInterval) {
                window.timerInterval = setInterval(() => updateTimer(s.free_deploy_until), 1000);
            }
        }

        // Render VPS slots list dynamically
        const vpsContainer = document.getElementById('vpsSlotsContainer');
        const ghSelect = document.getElementById('ghVpsSlot');
        const zipSelect = document.getElementById('zipVpsSlot');

        if (vpsContainer && s.vps_slots) {
            if (!s.vps_slots.length) {
                vpsContainer.innerHTML = '<p style="font-size: 11px; color: var(--muted)">No active VPS slots. Buy a high-performance VPS below to deploy!</p>';
            } else {
                vpsContainer.innerHTML = s.vps_slots.map(vs => `
                    <div style="display: flex; justify-content: space-between; align-items: center; background: var(--surface); border: 1px solid var(--border); padding: 10px 14px; border-radius: var(--radius-md)">
                        <div>
                            <span style="font-weight: 600; color: #fff; font-size:12px">${esc(vs.plan_name)}</span>
                            <span style="font-size: 10px; color: var(--muted)"> • Dedicated RAM: ${vs.ram_mb}MB</span>
                        </div>
                        <span class="status-badge status-${vs.status === 'running' ? 'running' : 'idle'}">${vs.status}</span>
                    </div>
                `).join('');
            }
        }

        // Populate Target VPS dropdowns
        if (ghSelect && zipSelect && s.vps_slots) {
            const options = s.vps_slots.map(vs => `<option value="${vs.id}">${vs.plan_name} (${vs.status})</option>`).join('');
            const defaultOpt = `<option value="">Auto-select Idle Slot (or Free Trial)</option>`;
            ghSelect.innerHTML = defaultOpt + options;
            zipSelect.innerHTML = defaultOpt + options;
        }

    } catch {}
}

function updateTimer(until) {
    const el = document.getElementById('statFreeTimer');
    if (!el) return;
    const diff = new Date(until) - new Date();
    if (diff <= 0) {
        el.textContent = 'Expired';
        el.style.color = 'var(--danger)';
        return;
    }
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    el.textContent = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

/* ===================== MANAGE DEPLOYMENTS ===================== */
async function loadDeployments() {
    const list = document.getElementById('deployList');
    list.innerHTML = '<div class="empty-state"><span class="spinner"></span><br>Loading...</div>';
    try {
        const deps = await api('/api/deployments');
        if (!deps.length) {
            list.innerHTML = '<div class="empty-state"><i class="fas fa-rocket"></i>No deployments yet.<br>Go to Deploy tab to create one.</div>';
            return;
        }
        list.innerHTML = deps.map(d => {
            let meta = d.type === 'github' ? '<i class="fab fa-github"></i> ' + esc(d.repo_url || '') : '<i class="fas fa-file-archive"></i> ZIP Upload';
            let slugSection = '';
            if (d.is_website) {
                const siteUrl = window.location.origin + '/site/' + d.slug;
                meta = `<i class="fas fa-globe"></i> Website: <a href="${siteUrl}" target="_blank" style="color:var(--accent); text-decoration:underline;" id="site-link-${d.id}">${siteUrl}</a><br><span style="font-size:11px;color:var(--warning)"><i class="fas fa-eye"></i> Visitors: ${d.visitor_count || 0} hits</span>`;
                slugSection = `
                <div style="margin-top:10px; padding-top:10px; border-top:1px dashed var(--border); display:flex; flex-direction:column; gap:6px;">
                    <div style="font-size:11px; color:var(--muted-light); font-weight:500;">Change Website URL Slug:</div>
                    <div class="flex gap-2">
                        <input type="text" id="slug-input-${d.id}" class="form-input text-sm" style="padding:6px 10px; max-width:200px;" value="${esc(d.slug)}" placeholder="new-slug">
                        <button class="btn btn-primary btn-sm" onclick="changeSlug(${d.id})" id="slug-btn-${d.id}">Save URL</button>
                    </div>
                </div>`;
            } else if (d.port) {
                meta += ' • Port: ' + d.port;
            }
            return `
            <div class="deploy-item">
                <div class="deploy-item-header">
                    <div>
                        <div class="deploy-item-name">${esc(d.name)} ${d.is_website ? '<span class="status-badge" style="background:rgba(0,145,255,0.1); color:var(--accent); margin-left:6px; font-size:10px">HTML Web</span>' : ''}</div>
                        <div class="deploy-item-meta">${meta}</div>
                    </div>
                    <span class="status-badge status-${d.status}">${statusDot(d.status)} ${d.status}</span>
                </div>
                ${slugSection}
                <div class="deploy-actions" style="margin-top: 10px;">
                    ${d.status === 'running' ? `<button class="btn btn-sm btn-secondary" onclick="stopDep(${d.id})"><i class="fas fa-stop"></i> Stop</button>` : `<button class="btn btn-sm btn-primary" onclick="startDep(${d.id})"><i class="fas fa-play"></i> Start</button>`}
                    <button class="btn btn-sm btn-secondary" onclick="viewLogs(${d.id})"><i class="fas fa-terminal"></i> Logs</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteDep(${d.id})"><i class="fas fa-trash"></i></button>
                </div>
            </div>
            `;
        }).join('');
    } catch { list.innerHTML = '<div class="empty-state">Failed to load</div>'; }
}

async function changeSlug(id) {
    const inp = document.getElementById(`slug-input-${id}`);
    const btn = document.getElementById(`slug-btn-${id}`);
    const slug = inp.value.trim().toLowerCase();
    if (!slug) { toast('Slug cannot be empty', 'error'); return; }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>';
    try {
        const data = await api(`/api/deployments/${id}/slug`, {
            method: 'POST',
            body: JSON.stringify({ slug })
        });
        toast('URL slug updated successfully!', 'success');
        const siteUrl = window.location.origin + '/site/' + data.slug;
        const link = document.getElementById(`site-link-${id}`);
        if (link) {
            link.href = siteUrl;
            link.textContent = siteUrl;
        }
    } catch (err) {
        // toast handles error already
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save URL';
    }
}

function statusDot(s) {
    if (s === 'running') return '<span style="width:5px;height:5px;background:var(--accent);border-radius:50%;display:inline-block"></span>';
    if (s === 'error') return '<span style="width:5px;height:5px;background:var(--danger);border-radius:50%;display:inline-block"></span>';
    return '<span style="width:5px;height:5px;background:var(--muted);border-radius:50%;display:inline-block"></span>';
}

async function startDep(id) {
    try { await api(`/api/deploy/${id}/start`, { method: 'POST' }); toast('Starting...', 'success'); setTimeout(loadDeployments, 2000); } catch {}
}
async function stopDep(id) {
    try { await api(`/api/deploy/${id}/stop`, { method: 'POST' }); toast('Stopped', 'success'); loadDeployments(); } catch {}
}
async function deleteDep(id) {
    if (!confirm('Delete this deployment permanently?')) return;
    try { await api(`/api/deploy/${id}`, { method: 'DELETE' }); toast('Deleted', 'success'); loadDeployments(); } catch {}
}
async function viewLogs(id) {
    currentDepId = id;
    document.getElementById('logModal').classList.add('show');
    document.getElementById('logContent').textContent = 'Loading logs...';
    pollLogs();
    logPolling = setInterval(pollLogs, 2000);
}
async function pollLogs() {
    if (!currentDepId) return;
    try {
        const data = await api(`/api/deploy/${currentDepId}/logs`);
        document.getElementById('logContent').textContent = data.logs || 'No logs yet...';
        document.getElementById('logStatus').textContent = data.status;
    } catch {}
}
function closeLogModal() {
    document.getElementById('logModal').classList.remove('show');
    if (logPolling) { clearInterval(logPolling); logPolling = null; }
    currentDepId = null;
}

/* ===================== DEPLOY FORM ===================== */
function initDeployForm() {
    const tabs = document.querySelectorAll('.deploy-tab-btn');
    tabs.forEach(t => t.addEventListener('click', () => {
        tabs.forEach(b => b.classList.remove('active'));
        t.classList.add('active');
        document.getElementById('githubForm').classList.toggle('hidden', t.dataset.target !== 'github');
        document.getElementById('zipForm').classList.toggle('hidden', t.dataset.target !== 'zip');
    }));

    const zipIsWebsite = document.getElementById('zipIsWebsite');
    if (zipIsWebsite) {
        zipIsWebsite.addEventListener('change', () => {
            const isWeb = zipIsWebsite.value === 'true';
            document.getElementById('zipBuildGroup').classList.toggle('hidden', isWeb);
            document.getElementById('zipDeployGroup').classList.toggle('hidden', isWeb);
            document.getElementById('zipEnvGroup').classList.toggle('hidden', isWeb);
        });
    }

    const ghForm = document.getElementById('ghDeployForm');
    if (ghForm) {
        ghForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = ghForm.querySelector('button[type="submit"]');
            btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Deploying...';
            try {
                const vpsSlotIdVal = document.getElementById('ghVpsSlot').value;
                const data = await api('/api/deploy/github', {
                    method: 'POST',
                    body: JSON.stringify({
                        name: document.getElementById('ghName').value,
                        repo_url: document.getElementById('ghRepo').value,
                        branch: document.getElementById('ghBranch').value,
                        build_command: document.getElementById('ghBuild').value,
                        deploy_command: document.getElementById('ghDeploy').value,
                        github_token: document.getElementById('ghToken').value,
                        env_vars: getEnvData('ghEnvList'),
                        vps_slot_id: vpsSlotIdVal ? parseInt(vpsSlotIdVal) : null
                    })
                });
                toast('Deployment started!', 'success');
                ghForm.reset();
                setTimeout(() => switchTab('manage'), 1000);
            } catch { btn.disabled = false; btn.innerHTML = '<i class="fas fa-rocket"></i> Deploy'; }
        });
    }

    const zipForm = document.getElementById('zipDeployForm');
    if (zipForm) {
        zipForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = zipForm.querySelector('button[type="submit"]');
            btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Uploading...';
            const fd = new FormData(zipForm);
            fd.set('env_vars', getEnvData('zipEnvList'));
            try {
                const res = await fetch(API + '/api/deploy/zip', { method: 'POST', body: fd });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error);
                toast('ZIP deployment started!', 'success');
                zipForm.reset();
                // Reset hidden state on select triggers
                if (zipIsWebsite) {
                    zipIsWebsite.value = 'false';
                    document.getElementById('zipBuildGroup').classList.remove('hidden');
                    document.getElementById('zipDeployGroup').classList.remove('hidden');
                    document.getElementById('zipEnvGroup').classList.remove('hidden');
                }
                setTimeout(() => switchTab('manage'), 1000);
            } catch (err) { toast(err.message, 'error'); btn.disabled = false; btn.innerHTML = '<i class="fas fa-upload"></i> Upload & Deploy'; }
        });
    }
}

/* ===================== SETTINGS ===================== */
async function loadSettings() {
    loadReferralInfo();
    loadChatMessages();
    loadTransactions();
}

async function loadReferralInfo() {
    try {
        const data = await api('/api/referral/info');
        document.getElementById('refCode').textContent = data.referral_code;
        document.getElementById('refLink').value = window.location.origin + '/register?ref=' + data.referral_code;
        document.getElementById('refEarned').textContent = '₹' + data.total_earned.toFixed(2);
        document.getElementById('refBalance').textContent = '₹' + data.wallet_balance.toFixed(2);
        const refList = document.getElementById('refList');
        if (!data.referrals.length) {
            refList.innerHTML = '<div class="text-muted text-sm">No referrals yet</div>';
        } else {
            refList.innerHTML = data.referrals.map(r => `
                <div class="flex justify-between items-center mb-2" style="padding:8px 0;border-bottom:1px solid var(--border)">
                    <div><span style="color:#fff;font-size:12px">${esc(r.username)}</span><br><span class="text-muted text-sm">${r.plan} plan</span></div>
                    <span class="text-accent text-sm">+₹${r.amount.toFixed(2)}</span>
                </div>
            `).join('');
        }
    } catch {}
}

function copyRefLink() {
    const inp = document.getElementById('refLink');
    inp.select(); navigator.clipboard.writeText(inp.value);
    toast('Link copied!', 'success');
}

async function requestWithdraw() {
    const amt = parseFloat(document.getElementById('withdrawAmt').value);
    if (!amt || amt <= 0) { toast('Enter valid amount', 'error'); return; }
    try { await api('/api/referral/withdraw', { method: 'POST', body: JSON.stringify({ amount: amt }) }); toast('Withdrawal requested!', 'success'); loadReferralInfo(); } catch {}
}

/* Chat */
async function loadChatMessages() {
    try {
        const msgs = await api('/api/chat');
        const container = document.getElementById('chatMessages');
        if (!msgs.length) {
            container.innerHTML = '<div class="text-muted text-sm" style="text-align:center;padding:20px">No messages yet. Start a conversation!</div>';
            return;
        }
        container.innerHTML = msgs.map(m => `
            <div class="chat-bubble ${m.sender}">
                ${esc(m.message)}
                <div class="chat-time">${new Date(m.date).toLocaleString()}</div>
            </div>
        `).join('');
        container.scrollTop = container.scrollHeight;
    } catch {}
}

async function sendChat() {
    const inp = document.getElementById('chatInput');
    const msg = inp.value.trim();
    if (!msg) return;
    inp.value = '';
    try { await api('/api/chat', { method: 'POST', body: JSON.stringify({ message: msg }) }); loadChatMessages(); } catch {}
}

/* Transactions */
async function loadTransactions() {
    try {
        const txs = await api('/api/transactions');
        const el = document.getElementById('txList');
        if (!txs.length) { el.innerHTML = '<div class="text-muted text-sm">No transactions</div>'; return; }
        el.innerHTML = txs.map(t => `
            <div class="flex justify-between mb-2" style="padding:8px 0;border-bottom:1px solid var(--border)">
                <div><span style="color:#fff;font-size:12px">${esc(t.description || t.type)}</span><br><span class="text-muted text-sm">${new Date(t.date).toLocaleDateString()}</span></div>
                <span class="${t.amount >= 0 ? 'text-accent' : 'text-danger'} text-sm">${t.amount >= 0 ? '+' : ''}₹${t.amount.toFixed(2)}</span>
            </div>
        `).join('');
    } catch {}
}

/* Payment Modal Logic */
let selectedPayAmount = 0;
let selectedPayCredits = 0;

function openPaymentModal(amount, credits) {
    selectedPayAmount = amount;
    selectedPayCredits = credits;
    document.getElementById('payAmountDisp').textContent = '₹' + amount;
    document.getElementById('paymentModal').classList.add('show');

    // Use pre-provided QR images for fixed tiers
    let qrPath = '/static/img/qr_99.png';
    if (amount >= 299) qrPath = '/static/img/qr_299.png';
    else if (amount >= 199) qrPath = '/static/img/qr_199.png';

    document.getElementById('payQR').src = qrPath;
    payNextStep(1);
}

function closePaymentModal() {
    document.getElementById('paymentModal').classList.remove('show');
}

function payNextStep(step) {
    document.getElementById('pay-step-1').classList.add('hidden');
    document.getElementById('pay-step-2').classList.add('hidden');
    document.getElementById('pay-step-3').classList.add('hidden');
    document.getElementById(`pay-step-${step}`).classList.remove('hidden');
}

async function submitPaymentRequest() {
    const name = document.getElementById('payName').value.trim();
    const number = document.getElementById('payNumber').value.trim();
    const txId = document.getElementById('payTxID').value.trim();

    if (!name || !number || !txId) { toast('All fields are required', 'error'); return; }

    const btn = document.getElementById('paySubmitBtn');
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Submitting...';

    try {
        await api('/api/payments/request', {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                number: number,
                transaction_id: txId,
                amount: selectedPayAmount
            })
        });
        toast('Request submitted! Admin will approve soon.', 'success');
        closePaymentModal();
    } catch {
        btn.disabled = false; btn.textContent = 'Submit Request';
    }
}

/* Env Row Helpers */
function addEnvRow(containerId) {
    const container = document.getElementById(containerId);
    const row = document.createElement('div');
    row.className = 'env-row';
    row.innerHTML = `
        <input type="text" class="env-id form-input" placeholder="ID (e.g. TOKEN)">
        <input type="text" class="env-key form-input" placeholder="Key (Value)">
        <button type="button" class="btn-del" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
    `;
    container.appendChild(row);
}

function getEnvData(containerId) {
    const rows = document.querySelectorAll(`#${containerId} .env-row`);
    const data = [];
    rows.forEach(r => {
        const id = r.querySelector('.env-id').value.trim();
        const key = r.querySelector('.env-key').value.trim();
        if (id && key) data.push({ id, key });
    });
    return JSON.stringify(data);
}

/* AI Assistant */
async function askAI() {
    const inp = document.getElementById('aiChatInput');
    const msg = inp.value.trim();
    if (!msg) return;

    const container = document.getElementById('aiChatMessages');
    container.innerHTML += `<div class="chat-bubble user">${esc(msg)}</div>`;
    inp.value = '';
    container.scrollTop = container.scrollHeight;

    // Simulate AI response
    setTimeout(() => {
        const responses = [
            "I'm analyzing your deployment logs... everything seems fine!",
            "To fix environment errors, make sure you've added your BOT_TOKEN in the environment variables.",
            "I recommend using a requirements.txt file for better dependency management.",
            "Your project structure looks great! Ready for deployment.",
            "If you face a port error, try changing the port or wait for the system to auto-assign one."
        ];
        const random = responses[Math.floor(Math.random() * responses.length)];
        container.innerHTML += `<div class="chat-bubble admin">${esc(random)}</div>`;
        container.scrollTop = container.scrollHeight;
    }, 1000);
}

/* Logout */
async function logout() {
    try { await api('/api/auth/logout', { method: 'POST' }); } catch {}
    window.location.href = '/login';
}

/* ===================== ADMIN PANEL ===================== */
function initAdmin() {
    // Check if already logged in
    const loginSection = document.getElementById('adminLogin');
    const panelSection = document.getElementById('adminPanel');
    const stored = sessionStorage.getItem('admin_logged');
    if (stored === 'true') {
        loginSection.classList.add('hidden');
        panelSection.classList.remove('hidden');
        loadAdminStats();
    }

    const loginForm = document.getElementById('adminLoginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = loginForm.querySelector('button');
            btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
            try {
                await api('/api/admin/login', {
                    method: 'POST',
                    body: JSON.stringify({
                        username: document.getElementById('adminUser').value,
                        password: document.getElementById('adminPass').value
                    })
                });
                sessionStorage.setItem('admin_logged', 'true');
                toast('Admin access granted', 'success');
                loginSection.classList.add('hidden');
                panelSection.classList.remove('hidden');
                loadAdminStats();
            } catch { btn.disabled = false; btn.textContent = 'Access Panel'; }
        });
    }

    document.querySelectorAll('.admin-nav-item[data-section]').forEach(btn => {
        btn.addEventListener('click', () => switchAdminSection(btn.dataset.section));
    });
}

function switchAdminSection(section) {
    document.querySelectorAll('.admin-nav-item').forEach(b => b.classList.remove('active'));
    document.querySelector(`.admin-nav-item[data-section="${section}"]`)?.classList.add('active');
    document.querySelectorAll('.admin-section').forEach(c => c.classList.add('hidden'));
    document.getElementById(`admin-${section}`)?.classList.remove('hidden');

    switch (section) {
        case 'dashboard': loadAdminStats(); break;
        case 'users': loadAdminUsers(); break;
        case 'deployments': loadAdminDeployments(); break;
        case 'payments': loadAdminPayments(); break;
        case 'blogs': loadAdminBlogs(); break;
        case 'transactions': loadAdminTransactions(); break;
        case 'chats': loadAdminChats(); break;
        case 'banned': loadAdminBanned(); break;
    }
}

async function loadAdminStats() {
    try {
        const s = await api('/api/admin/stats');
        document.getElementById('aStatUsers').textContent = s.total_users;
        document.getElementById('aStatActive').textContent = s.active_deployments;
        document.getElementById('aStatDeps').textContent = s.total_deployments;
        document.getElementById('aStatBanned').textContent = s.banned_users;
        document.getElementById('aStatRevenue').textContent = '₹' + s.total_revenue.toFixed(0);
        document.getElementById('aStatComm').textContent = '₹' + s.total_commissions.toFixed(0);
        document.getElementById('aStatChats').textContent = s.unread_chats;
    } catch {}
}

let allAdminUsers = [];
async function loadAdminUsers() {
    const el = document.getElementById('adminUsersTable');
    el.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:20px"><span class="spinner"></span></td></tr>';
    try {
        allAdminUsers = await api('/api/admin/users');
        renderAdminUsers(allAdminUsers);
    } catch { el.innerHTML = '<tr><td colspan="9" class="text-muted" style="text-align:center">Error</td></tr>'; }
}

function renderAdminUsers(users) {
    const el = document.getElementById('adminUsersTable');
    if (!users.length) { el.innerHTML = '<tr><td colspan="9" class="text-muted" style="text-align:center;padding:20px">No users found</td></tr>'; return; }
    el.innerHTML = users.map(u => `
        <tr>
            <td>${u.id}</td>
            <td style="color:#fff" title="Referred by ID: ${u.referred_by || 'Nobody'}">${esc(u.username)} ${u.is_banned ? '🚫' : ''}<br><span style="font-size:10px; color:var(--muted)">IP: ${esc(u.last_ip || 'N/A')}</span></td>
            <td style="font-size:11px">${esc(u.email)}</td>
            <td>
                <div class="flex items-center gap-1" style="min-width:110px">
                    <span id="pwd-text-${u.id}" class="hidden" style="font-family:monospace;font-size:11px">${esc(u.password_plain || 'N/A')}</span>
                    <span id="pwd-masked-${u.id}">••••••</span>
                    <button class="btn-icon" onclick="togglePwd(${u.id})" style="background:none;border:none;color:var(--accent);cursor:pointer;padding:2px;margin-left:auto" title="Show/Hide Password">
                        <i class="fas fa-eye" id="pwd-eye-${u.id}" style="font-size:12px"></i>
                    </button>
                </div>
            </td>
            <td>₹${u.wallet_balance.toFixed(1)}</td>
            <td>${u.credits}</td>
            <td><a href="#" onclick="filterDepsByUid(${u.id}); return false;" style="color:var(--accent)">${u.deployments}</a></td>
            <td style="font-size:10px">${new Date(u.created_at).toLocaleDateString()}</td>
            <td>
                <div class="flex gap-1" style="flex-wrap: wrap; max-width: 180px;">
                    <button class="admin-action-btn" onclick="openAdminChat(${u.id})" title="Chat"><i class="fas fa-comments"></i></button>
                    <button class="admin-action-btn" onclick="promptBalance(${u.id}, ${u.wallet_balance})" title="Quick Wallet"><i class="fas fa-wallet"></i></button>
                    <button class="admin-action-btn" onclick="promptCredits(${u.id}, ${u.credits})" title="Quick Credits"><i class="fas fa-coins"></i></button>
                    <button class="admin-action-btn" onclick="openAdminUserEditModal(${u.id})" title="Advanced Edit User"><i class="fas fa-user-pen"></i></button>
                    ${u.is_banned
                        ? `<button class="admin-action-btn success" onclick="adminUnban(${u.id})" title="Unban"><i class="fas fa-check"></i></button>`
                        : `<button class="admin-action-btn danger" onclick="adminBan(${u.id})" title="Ban"><i class="fas fa-ban"></i></button>`
                    }
                    ${u.last_ip ? `<button class="admin-action-btn danger" onclick="adminBanUserIp(${u.id})" title="Ban IP Device"><i class="fas fa-shield"></i></button>` : ''}
                    <button class="admin-action-btn danger" onclick="adminDeleteUser(${u.id})" title="Delete User Permanently"><i class="fas fa-user-xmark"></i></button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function adminBanUserIp(id) {
    if (!confirm('Ban user IP device from accessing EliteHosting? This will also stop all their deployments.')) return;
    try {
        await api(`/api/admin/users/${id}/ban-ip`, { method: 'POST' });
        toast('Device/IP and user banned!', 'success');
        loadAdminUsers();
        loadAdminStats();
    } catch {}
}

function togglePwd(uid) {
    const text = document.getElementById(`pwd-text-${uid}`);
    const masked = document.getElementById(`pwd-masked-${uid}`);
    const eye = document.getElementById(`pwd-eye-${uid}`);
    if (text.classList.contains('hidden')) {
        text.classList.remove('hidden');
        masked.classList.add('hidden');
        eye.classList.remove('fa-eye');
        eye.classList.add('fa-eye-slash');
    } else {
        text.classList.add('hidden');
        masked.classList.remove('hidden');
        eye.classList.remove('fa-eye-slash');
        eye.classList.add('fa-eye');
    }
}

function generateRandomPassword() {
    const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*";
    let pwd = "";
    for (let i = 0; i < 12; i++) {
        pwd += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    const inp = document.getElementById('editPassword');
    if (inp) inp.value = pwd;
}

function filterUsers() {
    const q = document.getElementById('userSearch').value.toLowerCase();
    const filtered = allAdminUsers.filter(u => u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
    renderAdminUsers(filtered);
}

function promptCredits(uid, current) {
    const amt = prompt(`Current credits: ${current}\nEnter amount to add (e.g. 5) or remove (e.g. -5):`);
    if (amt === null) return;
    const val = parseInt(amt);
    if (isNaN(val)) { toast('Invalid amount', 'error'); return; }
    api(`/api/admin/users/${uid}/credits`, { method: 'POST', body: JSON.stringify({ amount: val }) })
        .then(() => { toast('Credits updated', 'success'); loadAdminUsers(); })
        .catch(() => {});
}

async function adminBan(id) { if (!confirm('Ban this user?')) return; try { await api(`/api/admin/users/${id}/ban`, { method: 'POST' }); toast('Banned', 'success'); loadAdminUsers(); loadAdminStats(); } catch {} }
async function adminUnban(id) { try { await api(`/api/admin/users/${id}/unban`, { method: 'POST' }); toast('Unbanned', 'success'); loadAdminUsers(); loadAdminStats(); } catch {} }

function promptBalance(uid, current) {
    const amt = prompt(`Current balance: ₹${current}\nEnter amount (negative to remove):`);
    if (amt === null) return;
    const val = parseFloat(amt);
    if (isNaN(val)) { toast('Invalid amount', 'error'); return; }
    api(`/api/admin/users/${uid}/balance`, { method: 'POST', body: JSON.stringify({ amount: val }) })
        .then(() => { toast('Balance updated', 'success'); loadAdminUsers(); })
        .catch(() => {});
}

/* Advanced User Edit Modal handlers */
async function openAdminUserEditModal(uid) {
    try {
        const u = await api(`/api/admin/users/${uid}`);
        document.getElementById('editUserId').value = u.id;
        document.getElementById('editUsername').value = u.username;
        document.getElementById('editEmail').value = u.email;
        document.getElementById('editPassword').value = u.password_plain || '';
        document.getElementById('editPlan').value = u.plan;
        document.getElementById('editCredits').value = u.credits;
        document.getElementById('editWalletBalance').value = u.wallet_balance;
        document.getElementById('editReferralCode').value = u.referral_code || '';
        document.getElementById('editReferredBy').value = u.referred_by || '';

        if (u.free_deploy_until) {
            // Format ISO date for datetime-local input (YYYY-MM-DDTHH:MM)
            const dt = new Date(u.free_deploy_until);
            const formatted = dt.toISOString().slice(0, 16);
            document.getElementById('editFreeUntil').value = formatted;
        } else {
            document.getElementById('editFreeUntil').value = '';
        }

        document.getElementById('adminUserEditModal').classList.add('show');
    } catch (err) {}
}

function closeAdminUserEditModal() {
    document.getElementById('adminUserEditModal').classList.remove('show');
}

async function submitAdminUserEdit(e) {
    e.preventDefault();
    const uid = document.getElementById('editUserId').value;
    const payload = {
        username: document.getElementById('editUsername').value,
        email: document.getElementById('editEmail').value,
        password: document.getElementById('editPassword').value,
        plan: document.getElementById('editPlan').value,
        credits: parseInt(document.getElementById('editCredits').value),
        wallet_balance: parseFloat(document.getElementById('editWalletBalance').value),
        referral_code: document.getElementById('editReferralCode').value,
        referred_by: document.getElementById('editReferredBy').value,
        free_deploy_until: document.getElementById('editFreeUntil').value || null
    };

    try {
        await api(`/api/admin/users/${uid}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
        toast('User details updated successfully!', 'success');
        closeAdminUserEditModal();
        loadAdminUsers();
        loadAdminStats();
    } catch (err) {}
}

async function adminDeleteUser(uid) {
    if (!confirm('CRITICAL WARNING: Are you sure you want to permanently delete this user, ALL of their deployments, chat messages, payment history, and referrals? This cannot be undone!')) return;
    try {
        await api(`/api/admin/users/${uid}`, { method: 'DELETE' });
        toast('User and all associated data deleted successfully', 'success');
        loadAdminUsers();
        loadAdminStats();
    } catch (err) {}
}

/* Deployments handlers */
let allAdminDeps = [];
async function loadAdminDeployments(filterUid = null) {
    const el = document.getElementById('adminDepsTable');
    el.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:20px"><span class="spinner"></span></td></tr>';
    try {
        allAdminDeps = await api('/api/admin/deployments');
        if (filterUid) {
            const filtered = allAdminDeps.filter(d => d.user_id === filterUid);
            renderAdminDeps(filtered);
        } else {
            renderAdminDeps(allAdminDeps);
        }
    } catch { el.innerHTML = '<tr><td colspan="8" class="text-muted" style="text-align:center">Error</td></tr>'; }
}

function renderAdminDeps(deps) {
    const el = document.getElementById('adminDepsTable');
    if (!deps.length) { el.innerHTML = '<tr><td colspan="8" class="text-muted" style="text-align:center;padding:20px">No deployments found</td></tr>'; return; }
    el.innerHTML = deps.map(d => {
        let type_label = d.type;
        if (d.is_website) {
            type_label = `<span class="status-badge" style="background:rgba(0,145,255,0.1); color:var(--accent)">HTML Web</span>`;
        }
        let port_or_url = d.port || '-';
        if (d.is_website && d.slug) {
            const siteUrl = window.location.origin + '/site/' + d.slug;
            port_or_url = `<a href="${siteUrl}" target="_blank" style="color:var(--accent); text-decoration:underline;">/site/${d.slug}</a>`;
        }

        // Highlight high visitor deployments (visitors > 3)
        let alert_badge = '';
        if (d.is_website && d.visitor_count > 3) {
            alert_badge = `<div style="margin-top:4px"><span class="status-badge status-error" style="font-size:10px; background:#ff4444; color:#fff"><i class="fas fa-triangle-exclamation"></i> Heavy Traffic: ${d.visitor_count} hits</span></div>`;
        } else if (d.is_website) {
            alert_badge = `<div style="margin-top:4px"><span class="status-badge status-idle" style="font-size:10px">${d.visitor_count || 0} hits</span></div>`;
        }

        return `
        <tr>
            <td>${d.id}</td>
            <td style="color:#fff">${esc(d.username)}</td>
            <td>${esc(d.name)} ${alert_badge}</td>
            <td>${type_label}</td>
            <td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(d.repo_url)}">${esc(d.repo_url || '-')}</td>
            <td><span class="status-badge status-${d.status}">${d.status}</span></td>
            <td>${port_or_url}</td>
            <td>
                <div class="flex gap-1" style="flex-wrap: wrap; max-width: 220px;">
                    ${d.status === 'running'
                        ? `<button class="admin-action-btn danger" onclick="adminStopDep(${d.id})" title="Stop"><i class="fas fa-stop"></i></button>`
                        : `<button class="admin-action-btn success" onclick="adminStartDep(${d.id})" title="Start"><i class="fas fa-play"></i></button>`
                    }
                    <button class="admin-action-btn success" onclick="adminRestartDep(${d.id})" title="Restart"><i class="fas fa-arrows-rotate"></i></button>
                    <button class="admin-action-btn" onclick="adminViewDepLogs(${d.id})" title="Logs"><i class="fas fa-terminal"></i></button>
                    <button class="admin-action-btn" onclick="adminShowDepInfo(${d.id})" title="Info"><i class="fas fa-info-circle"></i></button>
                    <button class="admin-action-btn" onclick="openAdminDepEditModal(${d.id})" title="Edit Settings"><i class="fas fa-sliders"></i></button>
                    <button class="admin-action-btn danger" onclick="adminDeleteDep(${d.id})" title="Delete"><i class="fas fa-trash"></i></button>
                </div>
            </td>
        </tr>
        `;
    }).join('');
}

function filterDeps() {
    const q = document.getElementById('depSearch').value.toLowerCase();
    const filtered = allAdminDeps.filter(d => d.name.toLowerCase().includes(q) || d.username.toLowerCase().includes(q));
    renderAdminDeps(filtered);
}

function filterDepsByUid(uid) {
    document.querySelectorAll('.admin-nav-item').forEach(b => b.classList.remove('active'));
    document.querySelector('.admin-nav-item[data-section="deployments"]')?.classList.add('active');
    document.querySelectorAll('.admin-section').forEach(c => c.classList.add('hidden'));
    document.getElementById('admin-deployments')?.classList.remove('hidden');
    loadAdminDeployments(uid);
    document.getElementById('depSearch').value = '';
}

function adminShowDepInfo(id) {
    const d = allAdminDeps.find(dep => dep.id === id);
    if (!d) return;
    let info = `Name: ${d.name}\nType: ${d.type}\nUser ID: ${d.user_id}\nEntry: ${d.entry_file || 'auto'}\nCreated: ${new Date(d.created_at).toLocaleString()}\n\nEnvironment Variables:\n${d.env_vars || 'None'}`;
    alert(info);
}

async function adminStartDep(id) {
    try {
        await api(`/api/admin/deployments/${id}/start`, { method: 'POST' });
        toast('Start command issued', 'success');
        setTimeout(() => loadAdminDeployments(), 1000);
    } catch {}
}

async function adminRestartDep(id) {
    try {
        await api(`/api/admin/deployments/${id}/restart`, { method: 'POST' });
        toast('Restart command issued', 'success');
        setTimeout(() => loadAdminDeployments(), 1000);
    } catch {}
}

async function adminStopDep(id) {
    try {
        await api(`/api/admin/deployments/${id}/stop`, { method: 'POST' });
        toast('Stopped', 'success');
        loadAdminDeployments();
    } catch {}
}

async function adminDeleteDep(id) {
    if (!confirm('Are you sure you want to permanently delete this deployment and clean up its directories?')) return;
    try {
        await api(`/api/admin/deployments/${id}/delete`, { method: 'DELETE' });
        toast('Deleted', 'success');
        loadAdminDeployments();
    } catch {}
}

/* Edit Deployment handlers */
async function openAdminDepEditModal(id) {
    try {
        const d = await api(`/api/admin/deployments/${id}`);
        document.getElementById('editDepId').value = d.id;
        document.getElementById('editDepName').value = d.name;
        document.getElementById('editDepRepo').value = d.repo_url || '';
        document.getElementById('editDepBranch').value = d.branch || 'main';
        document.getElementById('editDepBuild').value = d.build_command || '';
        document.getElementById('editDepDeploy').value = d.deploy_command || '';
        document.getElementById('editDepEnv').value = d.env_vars || '';

        document.getElementById('adminDepEditModal').classList.add('show');
    } catch (err) {}
}

function closeAdminDepEditModal() {
    document.getElementById('adminDepEditModal').classList.remove('show');
}

async function submitAdminDepEdit(e) {
    e.preventDefault();
    const id = document.getElementById('editDepId').value;
    const payload = {
        name: document.getElementById('editDepName').value,
        repo_url: document.getElementById('editDepRepo').value,
        branch: document.getElementById('editDepBranch').value,
        build_command: document.getElementById('editDepBuild').value,
        deploy_command: document.getElementById('editDepDeploy').value,
        env_vars: document.getElementById('editDepEnv').value
    };

    try {
        await api(`/api/admin/deployments/${id}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
        toast('Deployment settings updated successfully!', 'success');
        closeAdminDepEditModal();
        loadAdminDeployments();
    } catch (err) {}
}

/* Blog Management handlers */
async function loadAdminBlogs() {
    const el = document.getElementById('adminBlogsTable');
    el.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px"><span class="spinner"></span></td></tr>';
    try {
        const blogs = await api('/api/admin/blogs');
        renderAdminBlogs(blogs);
    } catch { el.innerHTML = '<tr><td colspan="6" class="text-muted" style="text-align:center">Error loading blogs</td></tr>'; }
}

function renderAdminBlogs(blogs) {
    const el = document.getElementById('adminBlogsTable');
    if (!blogs.length) { el.innerHTML = '<tr><td colspan="6" class="text-muted" style="text-align:center;padding:20px">No blog posts found</td></tr>'; return; }
    el.innerHTML = blogs.map(b => `
        <tr>
            <td>${b.id}</td>
            <td style="color:#fff; font-weight: 500">${esc(b.title)}</td>
            <td><code>${esc(b.slug)}</code></td>
            <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${esc(b.excerpt || '-')}</td>
            <td>${new Date(b.created_at).toLocaleDateString()}</td>
            <td>
                <div class="flex gap-1">
                    <button class="admin-action-btn" onclick="openBlogEditModal(${b.id})" title="Edit Blog"><i class="fas fa-pen"></i></button>
                    <button class="admin-action-btn danger" onclick="adminDeleteBlog(${b.id})" title="Delete Blog"><i class="fas fa-trash"></i></button>
                </div>
            </td>
        </tr>
    `).join('');
}

function openBlogCreateModal() {
    document.getElementById('editBlogId').value = '';
    document.getElementById('editBlogTitle').value = '';
    document.getElementById('editBlogSlug').value = '';
    document.getElementById('editBlogExcerpt').value = '';
    document.getElementById('editBlogContent').value = '';
    document.getElementById('blogModalTitle').innerHTML = '<i class="fas fa-pen-nib" style="color:var(--accent);margin-right:8px"></i>Create Blog Post';
    document.getElementById('blogSubmitBtn').textContent = 'Publish Post';
    document.getElementById('adminBlogEditModal').classList.add('show');
}

async function openBlogEditModal(bid) {
    try {
        // Find blog inside local list or fetch blogs again
        const blogs = await api('/api/admin/blogs');
        const b = blogs.find(item => item.id === bid);
        if (!b) return;

        document.getElementById('editBlogId').value = b.id;
        document.getElementById('editBlogTitle').value = b.title;
        document.getElementById('editBlogSlug').value = b.slug;
        document.getElementById('editBlogExcerpt').value = b.excerpt || '';
        document.getElementById('editBlogContent').value = b.content;

        document.getElementById('blogModalTitle').innerHTML = '<i class="fas fa-pen-nib" style="color:var(--accent);margin-right:8px"></i>Edit Blog Post';
        document.getElementById('blogSubmitBtn').textContent = 'Save Changes';
        document.getElementById('adminBlogEditModal').classList.add('show');
    } catch (err) {}
}

function closeAdminBlogEditModal() {
    document.getElementById('adminBlogEditModal').classList.remove('show');
}

async function submitAdminBlogEdit(e) {
    e.preventDefault();
    const bid = document.getElementById('editBlogId').value;
    const payload = {
        title: document.getElementById('editBlogTitle').value,
        slug: document.getElementById('editBlogSlug').value,
        excerpt: document.getElementById('editBlogExcerpt').value,
        content: document.getElementById('editBlogContent').value
    };

    const isEdit = !!bid;
    const url = isEdit ? `/api/admin/blogs/${bid}` : '/api/admin/blogs';
    const method = isEdit ? 'PUT' : 'POST';

    try {
        await api(url, {
            method: method,
            body: JSON.stringify(payload)
        });
        toast(isEdit ? 'Blog post updated!' : 'Blog post published!', 'success');
        closeAdminBlogEditModal();
        loadAdminBlogs();
    } catch (err) {}
}

async function adminDeleteBlog(bid) {
    if (!confirm('Are you sure you want to permanently delete this blog post?')) return;
    try {
        await api(`/api/admin/blogs/${bid}`, { method: 'DELETE' });
        toast('Blog post deleted successfully', 'success');
        loadAdminBlogs();
    } catch (err) {}
}

/* Global Transactions handlers */
let allAdminTransactions = [];
async function loadAdminTransactions() {
    const el = document.getElementById('adminTransactionsTable');
    el.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px"><span class="spinner"></span></td></tr>';
    try {
        allAdminTransactions = await api('/api/admin/transactions');
        renderAdminTransactions(allAdminTransactions);
    } catch { el.innerHTML = '<tr><td colspan="6" class="text-muted" style="text-align:center">Error loading transactions</td></tr>'; }
}

function renderAdminTransactions(txs) {
    const el = document.getElementById('adminTransactionsTable');
    if (!txs.length) { el.innerHTML = '<tr><td colspan="6" class="text-muted" style="text-align:center;padding:20px">No transaction records</td></tr>'; return; }
    el.innerHTML = txs.map(t => `
        <tr>
            <td>${t.id}</td>
            <td style="color:#fff">${esc(t.username)}</td>
            <td><code>${t.tx_type}</code></td>
            <td class="${t.amount >= 0 ? 'text-accent' : 'text-danger'}">₹${t.amount.toFixed(2)}</td>
            <td>${esc(t.description || '-')}</td>
            <td style="font-size:11px">${new Date(t.created_at).toLocaleString()}</td>
        </tr>
    `).join('');
}

function filterTransactions() {
    const q = document.getElementById('txSearch').value.toLowerCase();
    const filtered = allAdminTransactions.filter(t =>
        t.username.toLowerCase().includes(q) ||
        (t.description && t.description.toLowerCase().includes(q)) ||
        t.tx_type.toLowerCase().includes(q)
    );
    renderAdminTransactions(filtered);
}

async function loadAdminPayments() {
    const el = document.getElementById('adminPaymentsTable');
    el.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:20px"><span class="spinner"></span></td></tr>';
    try {
        const reqs = await api('/api/admin/payments');
        if (!reqs.length) { el.innerHTML = '<tr><td colspan="8" class="text-muted" style="text-align:center;padding:20px">No payment requests</td></tr>'; return; }
        el.innerHTML = reqs.map(r => `
            <tr>
                <td>${r.id}</td>
                <td>${esc(r.username)}</td>
                <td style="font-size:11px">${esc(r.name)}<br>${esc(r.number)}</td>
                <td>₹${r.amount}</td>
                <td>${r.credits === 3 ? 'Pro 1GB VPS' : r.credits === 2 ? 'Lite 512MB VPS' : 'Micro 256MB VPS'}</td>
                <td><code style="font-size:10px">${esc(r.transaction_id)}</code></td>
                <td><span class="status-badge status-${r.status}">${r.status}</span></td>
                <td>
                    ${r.status === 'pending' ? `
                        <button class="admin-action-btn success" onclick="adminApprovePayment(${r.id})">Approve</button>
                        <button class="admin-action-btn danger" onclick="adminRejectPayment(${r.id})">Reject</button>
                    ` : '-'}
                </td>
            </tr>
        `).join('');
    } catch { el.innerHTML = '<tr><td colspan="8" class="text-muted" style="text-align:center">Error loading payments</td></tr>'; }
}

async function adminApprovePayment(id) {
    if (!confirm('Approve this payment and add credits?')) return;
    try { await api(`/api/admin/payments/${id}/approve`, { method: 'POST' }); toast('Approved!', 'success'); loadAdminPayments(); loadAdminStats(); } catch {}
}

async function adminRejectPayment(id) {
    if (!confirm('Reject this payment?')) return;
    try { await api(`/api/admin/payments/${id}/reject`, { method: 'POST' }); toast('Rejected', 'error'); loadAdminPayments(); } catch {}
}

let adminLogDepId = null;
let adminLogPolling = null;
async function adminViewDepLogs(id) {
    adminLogDepId = id;
    document.getElementById('adminLogModal').classList.add('show');
    document.getElementById('adminLogContent').textContent = 'Loading...';
    adminLogPoll();
    adminLogPolling = setInterval(adminLogPoll, 2000);
}
async function adminLogPoll() {
    if (!adminLogDepId) return;
    try { const d = await api(`/api/admin/deployments/${adminLogDepId}/logs`); document.getElementById('adminLogContent').textContent = d.logs || 'No logs'; } catch {}
}
function closeAdminLogModal() {
    document.getElementById('adminLogModal').classList.remove('show');
    if (adminLogPolling) { clearInterval(adminLogPolling); adminLogPolling = null; }
    adminLogDepId = null;
}

/* Admin Chats */
let adminChatUserId = null;
let adminChatPolling = null;

async function loadAdminChats() {
    try {
        const chats = await api('/api/admin/chats');
        const list = document.getElementById('adminChatUserList');

        // If an active user chat is open but not in the conversation list, add a temporary item
        if (adminChatUserId && !chats.some(c => c.user_id === adminChatUserId)) {
            const u = allAdminUsers.find(item => item.id === adminChatUserId);
            chats.unshift({
                user_id: adminChatUserId,
                username: u ? u.username : `User #${adminChatUserId}`,
                last_message: 'No messages yet...',
                last_date: new Date().toISOString(),
                unread: 0
            });
        }

        if (!chats.length) {
            list.innerHTML = '<div class="text-muted text-sm" style="padding:20px;text-align:center">No conversations</div>';
            return;
        }

        list.innerHTML = chats.map(c => `
            <div class="admin-chat-user-item ${c.user_id === adminChatUserId ? 'active' : ''}" data-uid="${c.user_id}" onclick="openAdminChat(${c.user_id})">
                <div class="name">${esc(c.username)} ${c.unread ? '<span class="unread-dot"></span>' : ''}</div>
                <div class="preview">${esc(c.last_message)}</div>
            </div>
        `).join('');
    } catch {}
}

async function openAdminChat(uid) {
    adminChatUserId = uid;
    switchAdminSection('chats');
    document.getElementById('adminChatWindow').classList.remove('hidden');
    if (adminChatPolling) clearInterval(adminChatPolling);
    await refreshAdminChat();
    adminChatPolling = setInterval(refreshAdminChat, 3000);
}

async function refreshAdminChat() {
    if (!adminChatUserId) return;
    try {
        const data = await api(`/api/admin/chats/${adminChatUserId}`);
        document.getElementById('adminChatHeader').textContent = data.username;
        const msgs = document.getElementById('adminChatMsgs');
        msgs.innerHTML = data.messages.map(m => `
            <div class="chat-bubble ${m.sender}" style="margin-bottom:10px">
                ${esc(m.message)}
                <div class="chat-time">${new Date(m.date).toLocaleString()}</div>
            </div>
        `).join('');
        msgs.scrollTop = msgs.scrollHeight;
    } catch {}
}

async function adminReply() {
    const inp = document.getElementById('adminChatInput');
    const msg = inp.value.trim();
    if (!msg || !adminChatUserId) return;
    inp.value = '';
    try { await api(`/api/admin/chats/${adminChatUserId}/reply`, { method: 'POST', body: JSON.stringify({ message: msg }) }); refreshAdminChat(); loadAdminChats(); } catch {}
}

async function loadAdminBanned() {
    try {
        const ips = await api('/api/admin/banned-ips');
        const el = document.getElementById('adminBannedList');
        if (!ips.length) { el.innerHTML = '<div class="text-muted text-sm" style="padding:20px;text-align:center">No banned devices</div>'; return; }
        el.innerHTML = ips.map(ip => `
            <div class="flex justify-between items-center mb-2" style="padding:10px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm)">
                <div><span style="color:#fff;font-size:12px">${esc(ip.ip)}</span><br><span class="text-muted text-sm">Reason: ${esc(ip.reason)} (${ip.attempts || 0} failed attempts)</span></div>
                <button class="admin-action-btn success" onclick="unbanIp('${ip.id}')">Unban</button>
            </div>
        `).join('');
    } catch {}
}

async function unbanIp(id) { try { await api(`/api/admin/banned-ips/${id}/unban`, { method: 'POST' }); toast('IP unbanned', 'success'); loadAdminBanned(); } catch {} }

async function manuallyBanIp() {
    const ip = prompt("Enter IP Address to ban:");
    if (!ip) return;
    const reason = prompt("Enter ban reason:", "Manual administrative ban");
    try {
        await api('/api/admin/banned-ips/add', {
            method: 'POST',
            body: JSON.stringify({ ip: ip, reason: reason })
        });
        toast('IP banned successfully!', 'success');
        loadAdminBanned();
    } catch {}
}

async function adminLogout() {
    try { await api('/api/admin/logout', { method: 'POST' }); } catch {}
    sessionStorage.removeItem('admin_logged');
    location.reload();
}

/* ===================== UTILS ===================== */
function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
