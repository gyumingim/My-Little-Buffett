<script lang="ts">
  import { goto } from '$app/navigation';
  import { Button, Card, Input } from '$shared/ui';

  let corpCode = '';
  let corpName = '';
  let bsnsYear = new Date().getFullYear().toString();
  let fsDiv = 'OFS';

  const years = Array.from({ length: 5 }, (_, i) => (new Date().getFullYear() - i).toString());

  // 샘플 기업들
  const sampleCompanies = [
    { code: '00126380', name: '삼성전자' },
    { code: '00164742', name: '현대자동차' },
    { code: '00155355', name: '풀무원' },
  ];

  function handleAnalysis() {
    if (!corpCode || !corpName || !bsnsYear) {
      alert('모든 필드를 입력해주세요.');
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
          <label class="input-label">사업연도</label>
          <select class="select" bind:value={bsnsYear}>
            {#each years as year}
              <option value={year}>{year}년</option>
            {/each}
          </select>
        </div>

        <div class="input-group">
          <label class="input-label">재무제표 구분</label>
          <select class="select" bind:value={fsDiv}>
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

  <section class="indicators-intro">
    <h2>5대 투자 지표</h2>
    <div class="indicator-grid">
      <div class="indicator-item">
        <div class="indicator-icon">💰</div>
        <h3>현금 창출 능력</h3>
        <p>영업활동현금흐름 vs 당기순이익을 비교하여 실제 현금 창출력을 평가합니다.</p>
      </div>

      <div class="indicator-item">
        <div class="indicator-icon">🛡️</div>
        <h3>이자보상배율</h3>
        <p>영업이익으로 이자비용을 몇 배나 감당할 수 있는지 재무 안정성을 측정합니다.</p>
      </div>

      <div class="indicator-item">
        <div class="indicator-icon">📈</div>
        <h3>영업이익 성장률</h3>
        <p>전년 대비 영업이익 증가율로 기업의 성장성을 확인합니다.</p>
      </div>

      <div class="indicator-item">
        <div class="indicator-icon">⚠️</div>
        <h3>희석 가능 물량</h3>
        <p>전환사채 등으로 인한 잠재적 주식 희석 위험을 분석합니다.</p>
      </div>

      <div class="indicator-item">
        <div class="indicator-icon">👔</div>
        <h3>내부자 거래</h3>
        <p>임원 및 주요주주의 순매수 동향으로 내부자 확신도를 파악합니다.</p>
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

  .indicators-intro {
    margin-top: 4rem;
  }

  .indicators-intro h2 {
    text-align: center;
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 2rem;
  }

  .indicator-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1.5rem;
  }

  .indicator-item {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius-lg);
    padding: 1.5rem;
    text-align: center;
  }

  .indicator-icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
  }

  .indicator-item h3 {
    font-size: 1.125rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .indicator-item p {
    font-size: 0.875rem;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  @media (max-width: 768px) {
    .hero h1 {
      font-size: 1.75rem;
    }

    .form-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
