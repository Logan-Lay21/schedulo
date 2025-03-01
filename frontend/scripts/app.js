// 状態管理用の変数
let user = null;
let assignments = [];
// DOM要素の取得
const rootElement = document.getElementById('root');
// Googleログインの初期化
function initializeGoogleLogin() {
  window.google.accounts.id.initialize({
    client_id: 'YOUR_GOOGLE_CLIENT_ID',
    callback: handleCredentialResponse,
  });
  window.google.accounts.id.renderButton(
    document.getElementById('google-login-btn'),
    { theme: 'outline', size: 'large' }
  );
}
// ログイン成功時の処理
function handleCredentialResponse(response) {
  const token = response.credential;
  localStorage.setItem('google_token', token);
  fetchUserProfile(token);
}
// ユーザープロフィールの取得
async function fetchUserProfile(token) {
  try {
    const profileResponse = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
      headers: { Authorization: `Bearer ${token}` },
    });
    const profileData = await profileResponse.json();
    user = profileData;
    renderApp();
  } catch (error) {
    console.error('プロフィール取得エラー:', error);
  }
}
// 課題データの取得
async function fetchAssignments() {
  try {
    const response = await fetch('/api/assignments');
    assignments = await response.json();
    renderApp();
  } catch (error) {
    console.error('課題取得エラー:', error);
  }
}
// アプリのレンダリング
function renderApp() {
  rootElement.innerHTML = `
    <header>
      ${user ? `
        <div class="profile">
          <img src="${user.picture}" alt="${user.name}" />
          <span>${user.name}</span>
          <button onclick="logout()">ログアウト</button>
        </div>
      ` : `
        <div id="google-login-btn"></div>
      `}
    </header>
    <main class="dashboard">
      <section class="assignment-list">
        <h2>課題一覧</h2>
        ${assignments.map(assignment => `
          <div class="assignment-item">
            <h3>${assignment.course}</h3>
            <p>${assignment.title}</p>
            <p>期限: ${new Date(assignment.due).toLocaleDateString()}</p>
          </div>
        `).join('')}
      </section>
    </main>
  `;
  if (!user) {
    initializeGoogleLogin();
  }
}
// ログアウト処理
function logout() {
  localStorage.removeItem('google_token');
  user = null;
  renderApp();
}
// 初期化
function init() {
  const token = localStorage.getItem('google_token');
  if (token) {
    fetchUserProfile(token);
  }
  fetchAssignments();
  renderApp();
}
// アプリケーションの起動
init();