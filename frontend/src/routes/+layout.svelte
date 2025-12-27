<script lang="ts">
  import '$lib/app/styles/global.css';
</script>

<div class="app">
  <header class="header">
    <div class="container header-content">
      <a href="/" class="logo">
        <span class="logo-icon">📊</span>
        <span class="logo-text">My Little Buffett</span>
      </a>
      <nav class="nav">
        <a href="/">홈</a>
        <a href="/screener">스크리너</a>
        <a href="/backtest">백테스팅</a>
        <a href="https://opendart.fss.or.kr" target="_blank" rel="noopener">OpenDART</a>
      </nav>
    </div>
  </header>

  <main class="main">
    <slot />
  </main>

  <footer class="footer">
    <div class="container footer-content">
      <p>5대 투자 지표 분석 시스템 | OpenDART API 활용</p>
    </div>
  </footer>
</div>

<style>
  .app {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .header {
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 64px;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    text-decoration: none;
    color: var(--text-primary);
  }

  .logo-icon {
    font-size: 1.5rem;
  }

  .logo-text {
    font-size: 1.25rem;
    font-weight: 700;
  }

  .nav {
    display: flex;
    gap: 1.5rem;
  }

  .nav a {
    color: var(--text-secondary);
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s;
  }

  .nav a:hover {
    color: var(--color-primary);
  }

  .main {
    flex: 1;
    padding: 2rem 0;
  }

  .footer {
    background: var(--bg-tertiary);
    border-top: 1px solid var(--border-color);
    padding: 1.5rem 0;
  }

  .footer-content {
    text-align: center;
  }

  .footer p {
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin: 0;
  }
</style>
