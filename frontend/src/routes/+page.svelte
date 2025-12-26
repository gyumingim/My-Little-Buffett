<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$shared/api';
  import { Button, Card, Input } from '$shared/ui';
  import { getWatchlist, removeFromWatchlist, type WatchlistItem } from '$shared/utils';

  let corpCode = '';
  let corpName = '';
  let bsnsYear = new Date().getFullYear().toString();
  let fsDiv = 'OFS';

  let searchQuery = '';
  let searchResults: { corp_code: string; corp_name: string; stock_code: string; sector: string }[] = [];
  let showResults = false;
  let searchTimeout: ReturnType<typeof setTimeout>;
  let watchlist: WatchlistItem[] = [];

  const years = Array.from({ length: 5 }, (_, i) => (new Date().getFullYear() - i).toString());

  onMount(() => {
    watchlist = getWatchlist();
  });

  async function handleSearch() {
    if (searchQuery.length < 1) {
      searchResults = [];
      showResults = false;
      return;
    }

    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
      const res = await api.searchCompanies(searchQuery, 8);
      if (res.success && res.data) {
        searchResults = res.data as typeof searchResults;
        showResults = searchResults.length > 0;
      }
    }, 200);
  }

  function selectCompany(company: typeof searchResults[0]) {
    corpCode = company.corp_code;
    corpName = company.corp_name;
    searchQuery = company.corp_name;
    showResults = false;
  }

  function handleAnalysis() {
    if (!corpCode || !corpName) {
      alert('기업을 선택해주세요.');
      return;
    }
    goto(`/company/${corpCode}?name=${encodeURIComponent(corpName)}&year=${bsnsYear}&fs_div=${fsDiv}`);
  }

  function removeWatchlistItem(corpCode: string) {
    removeFromWatchlist(corpCode);
    watchlist = getWatchlist();
  }

  function goToCompany(item: WatchlistItem) {
    goto(`/company/${item.corp_code}?name=${encodeURIComponent(item.corp_name)}&year=${bsnsYear}&fs_div=${fsDiv}`);
  }
</script>

<svelte:head>
  <title>My Little Buffett - 5대 투자 지표 분석</title>
</svelte:head>

<div class="container">
  <section class="hero">
    <h1>5대 투자 지표 분석</h1>
    <p>워렌 버핏의 투자 원칙에 기반한 핵심 지표로 기업을 분석합니다.</p>
  </section>

  <Card title="기업 분석" subtitle="기업명 또는 종목코드로 검색하세요">
    <form class="analysis-form" on:submit|preventDefault={handleAnalysis}>
      <div class="search-container">
        <div class="search-input-wrapper">
          <input
            type="text"
            class="search-input"
            placeholder="기업명 또는 종목코드 검색 (예: 삼성전자, 005930)"
            bind:value={searchQuery}
            on:input={handleSearch}
            on:focus={() => showResults = searchResults.length > 0}
          />
          {#if showResults}
            <div class="search-results">
              {#each searchResults as company}
                <button
                  type="button"
                  class="search-result-item"
                  on:click={() => selectCompany(company)}
                >
                  <span class="result-name">{company.corp_name}</span>
                  <span class="result-info">{company.stock_code} | {company.sector}</span>
                </button>
              {/each}
            </div>
          {/if}
        </div>

        {#if corpName}
          <div class="selected-company">
            선택: <strong>{corpName}</strong>
          </div>
        {/if}
      </div>

      <div class="options-row">
        <div class="input-group">
          <label class="input-label" for="year-input">사업연도</label>
          <select id="year-input" class="select" bind:value={bsnsYear}>
            {#each years as year}
              <option value={year}>{year}년</option>
            {/each}
          </select>
        </div>

        <div class="input-group">
          <label class="input-label" for="fs-input">재무제표</label>
          <select id="fs-input" class="select" bind:value={fsDiv}>
            <option value="OFS">개별</option>
            <option value="CFS">연결</option>
          </select>
        </div>
      </div>

      <Button type="submit" variant="primary">분석 시작</Button>
    </form>
  </Card>

  {#if watchlist.length > 0}
    <section class="watchlist">
      <h2>★ 즐겨찾기</h2>
      <div class="watchlist-grid">
        {#each watchlist as item}
          <div class="watchlist-item">
            <button class="watchlist-link" on:click={() => goToCompany(item)}>
              {item.corp_name}
            </button>
            <button class="remove-btn" on:click={() => removeWatchlistItem(item.corp_code)}>×</button>
          </div>
        {/each}
      </div>
    </section>
  {/if}

  <section class="quick-actions">
    <h2>빠른 분석</h2>
    <div class="action-grid">
      <a href="/screener" class="action-card">
        <span class="action-icon">📊</span>
        <span class="action-title">우량주 스크리너</span>
        <span class="action-desc">5대 지표 기준 상위 종목</span>
      </a>
      <a href="/compare" class="action-card">
        <span class="action-icon">⚖️</span>
        <span class="action-title">기업 비교</span>
        <span class="action-desc">두 기업 지표 비교 분석</span>
      </a>
    </div>
  </section>

  <section class="indicators-intro">
    <h2>5대 투자 지표</h2>
    <div class="indicator-list">
      <div class="indicator-item">
        <span class="indicator-name">현금 창출 능력</span>
        <span class="indicator-desc">영업활동현금흐름 > 당기순이익</span>
      </div>
      <div class="indicator-item">
        <span class="indicator-name">이자보상배율</span>
        <span class="indicator-desc">영업이익 / 이자비용 >= 3.0</span>
      </div>
      <div class="indicator-item">
        <span class="indicator-name">영업이익 성장률</span>
        <span class="indicator-desc">전년 대비 15% 이상 성장</span>
      </div>
      <div class="indicator-item">
        <span class="indicator-name">희석 가능 물량</span>
        <span class="indicator-desc">전환사채 비율 5% 미만</span>
      </div>
      <div class="indicator-item">
        <span class="indicator-name">내부자 거래</span>
        <span class="indicator-desc">임원 순매수 2인 이상</span>
      </div>
    </div>
  </section>
</div>

<style>
  .hero {
    text-align: center;
    padding: 3rem 0;
  }

  .hero h1 {
    font-size: 2.5rem;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
  }

  .hero p {
    font-size: 1.125rem;
    color: var(--text-secondary);
  }

  .analysis-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .search-container {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .search-input-wrapper {
    position: relative;
  }

  .search-input {
    width: 100%;
    padding: 1rem;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    font-size: 1rem;
  }

  .search-input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .search-results {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid var(--border-color);
    border-top: none;
    border-radius: 0 0 var(--border-radius) var(--border-radius);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    z-index: 10;
    max-height: 300px;
    overflow-y: auto;
  }

  .search-result-item {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border: none;
    background: white;
    cursor: pointer;
    text-align: left;
    transition: background 0.2s;
  }

  .search-result-item:hover {
    background: var(--bg-tertiary);
  }

  .result-name {
    font-weight: 500;
  }

  .result-info {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .selected-company {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .options-row {
    display: flex;
    gap: 1rem;
  }

  .input-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .input-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .select {
    padding: 0.75rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    font-size: 1rem;
    background: white;
    cursor: pointer;
  }

  .select:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .watchlist {
    margin-top: 2rem;
  }

  .watchlist h2 {
    font-size: 1.125rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    color: #fbbf24;
  }

  .watchlist-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .watchlist-item {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    background: var(--bg-tertiary);
    border-radius: 9999px;
    padding-left: 0.75rem;
  }

  .watchlist-link {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    padding: 0.5rem 0;
  }

  .watchlist-link:hover {
    color: var(--color-primary);
  }

  .remove-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-secondary);
    font-size: 1rem;
    padding: 0.5rem 0.75rem;
  }

  .remove-btn:hover {
    color: var(--color-danger);
  }

  .quick-actions {
    margin-top: 3rem;
  }

  .quick-actions h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }

  .action-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }

  .action-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 1.5rem;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius-lg);
    text-decoration: none;
    color: inherit;
    transition: all 0.2s;
  }

  .action-card:hover {
    border-color: var(--color-primary);
    transform: translateY(-2px);
  }

  .action-icon {
    font-size: 2rem;
  }

  .action-title {
    font-weight: 600;
  }

  .action-desc {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .indicators-intro {
    margin-top: 3rem;
  }

  .indicators-intro h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }

  .indicator-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .indicator-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--bg-tertiary);
    border-radius: var(--border-radius);
  }

  .indicator-name {
    font-weight: 500;
  }

  .indicator-desc {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  @media (max-width: 768px) {
    .hero h1 {
      font-size: 1.75rem;
    }

    .form-grid {
      grid-template-columns: 1fr;
    }

    .indicator-item {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.25rem;
    }
  }
</style>
