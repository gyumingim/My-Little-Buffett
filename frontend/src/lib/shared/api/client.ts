/**
 * API 클라이언트
 */

const API_BASE = '/api';

interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T | null;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const url = `${API_BASE}${endpoint}`;

  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      },
      ...options
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Unknown error',
      data: null
    };
  }
}

export const api = {
  /**
   * 5대 지표 종합 분석 조회
   */
  async getAnalysis(corpCode: string, corpName: string, bsnsYear: string, fsDiv: string = 'OFS') {
    const params = new URLSearchParams({
      corp_name: corpName,
      bsns_year: bsnsYear,
      fs_div: fsDiv
    });
    return request(`/indicators/analysis/${corpCode}?${params}`);
  },

  /**
   * 현금 창출 능력 지표 조회
   */
  async getCashGeneration(corpCode: string, bsnsYear: string, fsDiv: string = 'OFS') {
    const params = new URLSearchParams({ bsns_year: bsnsYear, fs_div: fsDiv });
    return request(`/indicators/cash-generation/${corpCode}?${params}`);
  },

  /**
   * 이자보상배율 지표 조회
   */
  async getInterestCoverage(corpCode: string, bsnsYear: string, fsDiv: string = 'OFS') {
    const params = new URLSearchParams({ bsns_year: bsnsYear, fs_div: fsDiv });
    return request(`/indicators/interest-coverage/${corpCode}?${params}`);
  },

  /**
   * 영업이익 성장률 지표 조회
   */
  async getOperatingGrowth(corpCode: string, bsnsYear: string, fsDiv: string = 'OFS') {
    const params = new URLSearchParams({ bsns_year: bsnsYear, fs_div: fsDiv });
    return request(`/indicators/operating-growth/${corpCode}?${params}`);
  },

  /**
   * 희석 가능 물량 비율 지표 조회
   */
  async getDilutionRisk(corpCode: string, bsnsYear: string) {
    const params = new URLSearchParams({ bsns_year: bsnsYear });
    return request(`/indicators/dilution-risk/${corpCode}?${params}`);
  },

  /**
   * 임원/주요주주 순매수 강도 지표 조회
   */
  async getInsiderTrading(corpCode: string) {
    return request(`/indicators/insider-trading/${corpCode}`);
  },

  /**
   * 재무제표 조회
   */
  async getFinancialStatements(corpCode: string, bsnsYear: string, reprtCode: string = '11011', fsDiv: string = 'OFS') {
    const params = new URLSearchParams({
      bsns_year: bsnsYear,
      reprt_code: reprtCode,
      fs_div: fsDiv
    });
    return request(`/statements/${corpCode}?${params}`);
  },

  /**
   * 임원 주식 보유 현황 조회
   */
  async getExecutiveStock(corpCode: string) {
    return request(`/disclosures/executive-stock/${corpCode}`);
  },

  /**
   * 전환사채 정보 조회
   */
  async getConvertibleBonds(corpCode: string, bgnDe: string, endDe: string) {
    const params = new URLSearchParams({ bgn_de: bgnDe, end_de: endDe });
    return request(`/disclosures/convertible-bonds/${corpCode}?${params}`);
  },

  /**
   * 트렌드 분석 (3개년)
   */
  async getTrend(corpCode: string, corpName: string, bsnsYear: string, fsDiv: string = 'OFS') {
    const params = new URLSearchParams({
      corp_name: corpName,
      bsns_year: bsnsYear,
      fs_div: fsDiv
    });
    return request(`/indicators/trend/${corpCode}?${params}`);
  },

  /**
   * 우량주 스캔
   */
  async scanStocks(year: string, fsDiv: string = 'OFS', limit: number = 10) {
    const params = new URLSearchParams({
      year,
      fs_div: fsDiv,
      limit: limit.toString()
    });
    return request(`/indicators/screener/scan?${params}`);
  },

  /**
   * 추천 종목 조회
   */
  async getTopPicks(year: string, fsDiv: string = 'OFS') {
    const params = new URLSearchParams({ year, fs_div: fsDiv });
    return request(`/indicators/screener/top-picks?${params}`);
  }
};

export type { ApiResponse };
