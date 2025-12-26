<script lang="ts">
  import { goto } from '$app/navigation';
  import { Button, Card, Input } from '$shared/ui';

  let corpCode = '';
  let corpName = '';
  let bsnsYear = new Date().getFullYear().toString();
  let fsDiv = 'OFS';

  const years = Array.from({ length: 5 }, (_, i) => (new Date().getFullYear() - i).toString());

  const sampleCompanies = [
    { code: '00126380', name: '삼성전자' },
    { code: '00164742', name: '현대자동차' },
    { code: '00401731', name: 'SK하이닉스' },
    { code: '00155355', name: '네이버' },
    { code: '00181710', name: '카카오' },
  ];

  function handleAnalysis() {
    if (!corpCode || !corpName) {
      alert('기업 고유번호와 기업명을 입력해주세요.');
      return;
    }
    goto(`/company/${corpCode}?name=${encodeURIComponent(corpName)}&year=${bsnsYear}&fs_div=${fsDiv}`);
  }

  function selectSample(company: { code: string; name: string }) {
    corpCode = company.code;
    corpName = company.name;
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

  <Card title="기업 분석" subtitle="OpenDART API를 활용한 재무제표 기반 분석">
    <form class="analysis-form" on:submit|preventDefault={handleAnalysis}>
      <div class="form-grid">
        <Input
          label="기업 고유번호"
          placeholder="8자리 (예: 00126380)"
          bind:value={corpCode}
          required
        />

        <Input
          label="기업명"
          placeholder="예: 삼성전자"
          bind:value={corpName}
          required
        />

        <div class="input-group">
          <label class="input-label" for="year-input">사업연도</label>
          <select id="year-input" class="select" bind:value={bsnsYear}>
            {#each years as year}
              <option value={year}>{year}년</option>
            {/each}
          </select>
        </div>

        <div class="input-group">
          <label class="input-label" for="fs-input">재무제표 구분</label>
          <select id="fs-input" class="select" bind:value={fsDiv}>
            <option value="OFS">개별 재무제표</option>
            <option value="CFS">연결 재무제표</option>
          </select>
        </div>
      </div>

      <div class="sample-companies">
        <span class="sample-label">샘플 기업:</span>
        {#each sampleCompanies as company}
          <button
            type="button"
            class="sample-btn"
            on:click={() => selectSample(company)}
          >
            {company.name}
          </button>
        {/each}
      </div>

      <Button type="submit" variant="primary">분석 시작</Button>
    </form>
  </Card>

  <section class="quick-actions">
    <h2>빠른 분석</h2>
    <div class="action-grid">
      <a href="/screener" class="action-card">
        <span class="action-icon">📊</span>
        <span class="action-title">우량주 스크리너</span>
        <span class="action-desc">5대 지표 기준 상위 종목</span>
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

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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

  .sample-companies {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .sample-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .sample-btn {
    padding: 0.375rem 0.75rem;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: 9999px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .sample-btn:hover {
    background: var(--border-color);
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
