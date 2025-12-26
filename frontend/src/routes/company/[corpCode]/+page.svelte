<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api } from '$shared/api';
  import { Loading, Card, Button } from '$shared/ui';
  import { IndicatorCard, ScoreGauge } from '$widgets/indicator-card';
  import { formatAmount, formatPercent, formatRatio } from '$shared/utils';

  interface AnalysisData {
    corp_code: string;
    corp_name: string;
    analysis_date: string;
    bsns_year: string;
    cash_generation: any;
    interest_coverage: any;
    operating_profit_growth: any;
    dilution_risk: any;
    insider_trading: any;
    overall_score: number;
    overall_signal: string;
    recommendation: string;
  }

  let loading = true;
  let error = '';
  let analysis: AnalysisData | null = null;

  $: corpCode = $page.params.corpCode;
  $: corpName = $page.url.searchParams.get('name') || '';
  $: bsnsYear = $page.url.searchParams.get('year') || new Date().getFullYear().toString();
  $: fsDiv = $page.url.searchParams.get('fs_div') || 'OFS';

  onMount(async () => {
    await fetchAnalysis();
  });

  async function fetchAnalysis() {
    loading = true;
    error = '';

    try {
      const response = await api.getAnalysis(corpCode, corpName, bsnsYear, fsDiv);

      if (response.success && response.data) {
        analysis = response.data as AnalysisData;
      } else {
        error = response.message || '분석 데이터를 가져오는데 실패했습니다.';
      }
    } catch (e) {
      error = '네트워크 오류가 발생했습니다.';
      console.error(e);
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>{corpName} 분석 결과 - My Little Buffett</title>
</svelte:head>

<div class="container">
  {#if loading}
    <Loading size="lg" text="분석 중입니다..." />
  {:else if error}
    <Card>
      <div class="error-state">
        <p class="error-message">{error}</p>
        <Button variant="secondary" on:click={() => history.back()}>돌아가기</Button>
      </div>
    </Card>
  {:else if analysis}
    <div class="analysis-header">
      <div class="company-info">
        <h1>{analysis.corp_name}</h1>
        <p>고유번호: {analysis.corp_code} | {analysis.bsns_year}년 사업보고서 기준</p>
      </div>
      <p class="analysis-date">분석일: {analysis.analysis_date}</p>
    </div>

    <div class="analysis-grid">
      <!-- 종합 점수 -->
      <Card title="종합 분석">
        <ScoreGauge
          score={analysis.overall_score}
          signal={analysis.overall_signal}
          recommendation={analysis.recommendation}
        />
      </Card>

      <!-- 5대 지표 -->
      <div class="indicators-section">
        <h2>5대 투자 지표</h2>

        <div class="indicators-grid">
          {#if analysis.cash_generation}
            <IndicatorCard
              name={analysis.cash_generation.name}
              description={analysis.cash_generation.description}
              signal={analysis.cash_generation.signal}
              signalDescription={analysis.cash_generation.signal_description}
              metrics={[
                { label: '영업활동현금흐름', value: formatAmount(analysis.cash_generation.operating_cash_flow) },
                { label: '당기순이익', value: formatAmount(analysis.cash_generation.net_income) },
              ]}
            />
          {/if}

          {#if analysis.interest_coverage}
            <IndicatorCard
              name={analysis.interest_coverage.name}
              description={analysis.interest_coverage.description}
              signal={analysis.interest_coverage.signal}
              signalDescription={analysis.interest_coverage.signal_description}
              metrics={[
                { label: '영업이익', value: formatAmount(analysis.interest_coverage.operating_income) },
                { label: '이자비용', value: formatAmount(analysis.interest_coverage.interest_expense) },
                { label: '이자보상배율', value: formatRatio(analysis.interest_coverage.ratio) },
              ]}
            />
          {/if}

          {#if analysis.operating_profit_growth}
            <IndicatorCard
              name={analysis.operating_profit_growth.name}
              description={analysis.operating_profit_growth.description}
              signal={analysis.operating_profit_growth.signal}
              signalDescription={analysis.operating_profit_growth.signal_description}
              metrics={[
                { label: '당기 영업이익', value: formatAmount(analysis.operating_profit_growth.current_operating_income) },
                { label: '전기 영업이익', value: formatAmount(analysis.operating_profit_growth.previous_operating_income) },
                { label: '성장률', value: formatPercent(analysis.operating_profit_growth.growth_rate) },
              ]}
            />
          {/if}

          {#if analysis.dilution_risk}
            <IndicatorCard
              name={analysis.dilution_risk.name}
              description={analysis.dilution_risk.description}
              signal={analysis.dilution_risk.signal}
              signalDescription={analysis.dilution_risk.signal_description}
              metrics={[
                { label: '전환 가능 주식수', value: analysis.dilution_risk.convertible_shares.toLocaleString() + '주' },
                { label: '총 발행 주식수', value: analysis.dilution_risk.total_shares.toLocaleString() + '주' },
                { label: '희석 비율', value: analysis.dilution_risk.dilution_ratio.toFixed(2) + '%' },
              ]}
            />
          {/if}

          {#if analysis.insider_trading}
            <IndicatorCard
              name={analysis.insider_trading.name}
              description={analysis.insider_trading.description}
              signal={analysis.insider_trading.signal}
              signalDescription={analysis.insider_trading.signal_description}
              metrics={[
                { label: '순매수 건수', value: analysis.insider_trading.net_buy_count + '건' },
                { label: '순매도 건수', value: analysis.insider_trading.net_sell_count + '건' },
                { label: 'CEO 매수', value: analysis.insider_trading.ceo_bought ? '있음' : '없음' },
              ]}
            />
          {/if}
        </div>
      </div>
    </div>

    <div class="actions">
      <Button variant="secondary" on:click={() => history.back()}>
        다른 기업 분석
      </Button>
      <Button variant="primary" on:click={() => window.print()}>
        결과 출력
      </Button>
    </div>
  {/if}
</div>

<style>
  .analysis-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 2rem;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .company-info h1 {
    font-size: 2rem;
    font-weight: 700;
    margin: 0;
  }

  .company-info p {
    color: var(--text-secondary);
    margin: 0.5rem 0 0;
  }

  .analysis-date {
    color: var(--text-muted);
    font-size: 0.875rem;
  }

  .analysis-grid {
    display: grid;
    gap: 2rem;
  }

  .indicators-section h2 {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
  }

  .indicators-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 1.5rem;
  }

  .error-state {
    text-align: center;
    padding: 2rem;
  }

  .error-message {
    color: var(--color-danger);
    margin-bottom: 1rem;
  }

  .actions {
    display: flex;
    justify-content: center;
    gap: 1rem;
    margin-top: 3rem;
    padding-bottom: 2rem;
  }

  @media (max-width: 768px) {
    .analysis-header {
      flex-direction: column;
    }

    .company-info h1 {
      font-size: 1.5rem;
    }

    .indicators-grid {
      grid-template-columns: 1fr;
    }
  }

  @media print {
    .actions {
      display: none;
    }
  }
</style>
