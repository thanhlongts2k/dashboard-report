// State Management
const state = {
    apiBaseUrl: 'http://127.0.0.1:8000',
    googleClientId: '',
    sessionToken: localStorage.getItem('knox_token') || '',
    sessionExpiry: localStorage.getItem('knox_expiry') || ''
};

// DOM Elements
const elements = {
    apiBaseUrlInput: document.getElementById('api-base-url'),
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    googleClientIdInput: document.getElementById('google-client-id'),
    btnInitGsi: document.getElementById('btn-init-gsi'),
    gsiWrapper: document.getElementById('gsi-button-wrapper'),
    manualIdTokenInput: document.getElementById('manual-id-token'),
    btnTestGoogleToken: document.getElementById('btn-test-google-token'),
    credUsernameInput: document.getElementById('cred-username'),
    credPasswordInput: document.getElementById('cred-password'),
    btnTestCredentials: document.getElementById('btn-test-credentials'),
    responseStatusBadge: document.getElementById('response-status-badge'),
    timeElapsedDisplay: document.getElementById('time-elapsed-display'),
    jsonResponseOutput: document.getElementById('json-response-output'),
    sessionBox: document.getElementById('session-box'),
    sessionTokenDisplay: document.getElementById('session-token-display'),
    sessionExpiryDisplay: document.getElementById('session-expiry-display'),
    btnCopyToken: document.getElementById('btn-copy-token'),
    btnClearSession: document.getElementById('btn-clear-session'),
    btnTestBuApi: document.getElementById('btn-test-bu-api'),
    toastContainer: document.getElementById('toast-container')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initTabNavigation();
    initEventListeners();
    updateSessionUI();
});

// Tab Navigation
function initTabNavigation() {
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabTarget = btn.getAttribute('data-tab');
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            elements.tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(tabTarget).classList.add('active');
        });
    });
}

// Event Listeners Initialization
function initEventListeners() {
    elements.apiBaseUrlInput.addEventListener('change', (e) => {
        state.apiBaseUrl = e.target.value.trim().replace(/\/+$/, '');
        showToast('Đã cập nhật API Base URL: ' + state.apiBaseUrl, 'info');
    });

    elements.btnInitGsi.addEventListener('click', initGoogleSDK);

    elements.btnTestGoogleToken.addEventListener('click', () => {
        const idToken = elements.manualIdTokenInput.value.trim();
        if (!idToken) {
            showToast('Vui lòng nhập chuỗi Google ID Token!', 'error');
            return;
        }
        sendGoogleLoginRequest(idToken);
    });

    elements.btnTestCredentials.addEventListener('click', () => {
        const username = elements.credUsernameInput.value.trim();
        const password = elements.credPasswordInput.value.trim();
        if (!username || !password) {
            showToast('Vui lòng nhập đủ Username và Password!', 'error');
            return;
        }
        sendCredentialsLoginRequest(username, password);
    });

    elements.btnCopyToken.addEventListener('click', () => {
        if (state.sessionToken) {
            navigator.clipboard.writeText(state.sessionToken);
            showToast('Đã sao chép Knox Token vào clipboard!', 'success');
        }
    });

    elements.btnClearSession.addEventListener('click', clearSession);

    elements.btnTestBuApi.addEventListener('click', testAuthenticatedApi);
}

// Initialize Google Sign-In SDK Button
function initGoogleSDK() {
    const clientId = elements.googleClientIdInput.value.trim();
    if (!clientId) {
        showToast('Vui lòng nhập Google Client ID hợp lệ!', 'error');
        return;
    }

    if (typeof google === 'undefined' || !google.accounts || !google.accounts.id) {
        showToast('Google Identity SDK chưa sẵn sàng. Hãy kiểm tra kết nối mạng!', 'error');
        return;
    }

    try {
        state.googleClientId = clientId;
        google.accounts.id.initialize({
            client_id: clientId,
            callback: handleGoogleSDKResponse
        });

        elements.gsiWrapper.innerHTML = '';
        google.accounts.id.renderButton(
            elements.gsiWrapper,
            { theme: 'outline', size: 'large', width: 300, text: 'signin_with' }
        );
        showToast('Đã khởi tạo Google Sign-In SDK nút bấm thành công!', 'success');
    } catch (err) {
        showToast('Lỗi nạp Google SDK: ' + err.message, 'error');
    }
}

// Google SDK Callback Handler
function handleGoogleSDKResponse(response) {
    if (response && response.credential) {
        showToast('Đã nhận Google ID Token từ SDK!', 'success');
        elements.manualIdTokenInput.value = response.credential;
        sendGoogleLoginRequest(response.credential);
    } else {
        showToast('Không nhận được credential từ Google!', 'error');
    }
}

// Send POST /api/google-login/
async function sendGoogleLoginRequest(idToken) {
    const url = `${getApiBaseUrl()}/api/google-login/`;
    const payload = { id_token: idToken };

    renderRequestStart(`POST ${url}`, payload);
    const startTime = performance.now();

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const timeElapsed = Math.round(performance.now() - startTime);
        const data = await response.json();

        renderResponseOutput(response.status, response.statusText, data, timeElapsed);

        if (response.ok && data.token) {
            saveSession(data.token, data.expiry);
            showToast('Đăng nhập Google SSO thành công!', 'success');
        } else {
            showToast('Đăng nhập thất bại: ' + (data.error || 'Bad Request'), 'error');
        }
    } catch (err) {
        const timeElapsed = Math.round(performance.now() - startTime);
        renderResponseOutput(0, 'Network Error', { error: 'Không thể kết nối đến Django Backend Server. Hãy chắc chắn Server đang chạy và CORS được bật!', details: err.message }, timeElapsed);
        showToast('Lỗi mạng/Kết nối Server!', 'error');
    }
}

// Send POST /api/login/ (Username/Password)
async function sendCredentialsLoginRequest(username, password) {
    const url = `${getApiBaseUrl()}/api/login/`;
    // Standard Django Knox login expects Basic Auth or POST username/password
    const payload = { username, password };

    renderRequestStart(`POST ${url}`, { username, password: '***' });
    const startTime = performance.now();

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + btoa(username + ':' + password)
            },
            body: JSON.stringify(payload)
        });

        const timeElapsed = Math.round(performance.now() - startTime);
        const data = await response.json();

        renderResponseOutput(response.status, response.statusText, data, timeElapsed);

        if (response.ok && data.token) {
            saveSession(data.token, data.expiry);
            showToast('Đăng nhập tài khoản thành công!', 'success');
        } else {
            showToast('Đăng nhập thất bại: Sai tài khoản hoặc mật khẩu!', 'error');
        }
    } catch (err) {
        const timeElapsed = Math.round(performance.now() - startTime);
        renderResponseOutput(0, 'Network Error', { error: 'Không thể kết nối Backend Server!', details: err.message }, timeElapsed);
        showToast('Lỗi mạng/Kết nối Server!', 'error');
    }
}

// Test Authenticated API with Knox Token (GET /api/business-units/)
async function testAuthenticatedApi() {
    if (!state.sessionToken) {
        showToast('Bạn chưa có Knox Token. Hãy đăng nhập trước!', 'error');
        return;
    }

    const url = `${getApiBaseUrl()}/api/business-units/`;
    renderRequestStart(`GET ${url}\nHeader: Authorization: Token ${state.sessionToken.substring(0, 10)}...`, null);
    const startTime = performance.now();

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Token ${state.sessionToken}`,
                'Content-Type': 'application/json'
            }
        });

        const timeElapsed = Math.round(performance.now() - startTime);
        const data = await response.json();

        renderResponseOutput(response.status, response.statusText, data, timeElapsed);

        if (response.ok) {
            showToast('Gọi API bảo mật thành công!', 'success');
        } else {
            showToast('Xác thực token bị từ chối!', 'error');
        }
    } catch (err) {
        const timeElapsed = Math.round(performance.now() - startTime);
        renderResponseOutput(0, 'Network Error', { error: err.message }, timeElapsed);
    }
}

// Helper: Get API Base URL
function getApiBaseUrl() {
    return elements.apiBaseUrlInput.value.trim().replace(/\/+$/, '') || 'http://127.0.0.1:8000';
}

// Save Session State
function saveSession(token, expiry) {
    state.sessionToken = token;
    state.sessionExpiry = expiry || '';
    localStorage.setItem('knox_token', token);
    if (expiry) localStorage.setItem('knox_expiry', expiry);
    updateSessionUI();
}

// Clear Session State
function clearSession() {
    state.sessionToken = '';
    state.sessionExpiry = '';
    localStorage.removeItem('knox_token');
    localStorage.removeItem('knox_expiry');
    updateSessionUI();
    showToast('Đã đăng xuất session!', 'info');
}

// Update Active Session UI
function updateSessionUI() {
    if (state.sessionToken) {
        elements.sessionBox.style.display = 'flex';
        elements.sessionTokenDisplay.textContent = state.sessionToken;
        elements.sessionExpiryDisplay.textContent = state.sessionExpiry ? new Date(state.sessionExpiry).toLocaleString('vi-VN') : 'Không giới hạn';
    } else {
        elements.sessionBox.style.display = 'none';
    }
}

// Render Response Output in Inspector
function renderRequestStart(reqInfo, body) {
    elements.responseStatusBadge.innerHTML = `<span class="status-pill status-idle"><i class="fa-solid fa-spinner fa-spin"></i> Đang gửi request...</span>`;
    elements.timeElapsedDisplay.textContent = '... ms';
    let outputText = `>>> REQUEST: ${reqInfo}\n`;
    if (body) outputText += `\nPAYLOAD:\n${JSON.stringify(body, null, 2)}\n\n`;
    elements.jsonResponseOutput.textContent = outputText + `>>> WAITING FOR SERVER RESPONSE...`;
}

function renderResponseOutput(status, statusText, data, timeElapsed) {
    elements.timeElapsedDisplay.textContent = `${timeElapsed} ms`;

    let statusClass = 'status-200';
    if (status >= 400 || status === 0) statusClass = 'status-400';

    const statusTextDisplay = status === 0 ? 'CONNECTION FAILED' : `${status} ${statusText}`;
    elements.responseStatusBadge.innerHTML = `<span class="status-pill ${statusClass}">${statusTextDisplay}</span>`;

    const formattedJson = JSON.stringify(data, null, 2);
    elements.jsonResponseOutput.textContent = `HTTP STATUS: ${statusTextDisplay}\nTIME: ${timeElapsed} ms\n\nRESPONSE JSON:\n${formattedJson}`;
}

// Toast Notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    let iconClass = 'fa-circle-info';
    if (type === 'success') iconClass = 'fa-circle-check';
    if (type === 'error') iconClass = 'fa-circle-xmark';

    toast.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${message}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
