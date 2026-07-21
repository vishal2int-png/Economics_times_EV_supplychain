const API_URL = 'http://localhost:8000/api';

export async function fetchFromAPI(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error fetching ${endpoint}:`, error);
    throw error;
  }
}

export const api = {
  // Common / Dashboard
  getDashboard: () => fetchFromAPI('/dashboard'),
  
  // Battery APM
  getFleetHealth: () => fetchFromAPI('/battery/fleet-health'),
  getVehicleBattery: (id) => fetchFromAPI(`/battery/vehicle/${id}`),
  getDegradation: (id) => fetchFromAPI(`/battery/degradation/${id}`),
  getBatteryAlerts: () => fetchFromAPI('/battery/alerts'),
  getMaintenanceSchedule: () => fetchFromAPI('/battery/maintenance-schedule'),

  // Fleet Readiness
  getReadinessScores: () => fetchFromAPI('/fleet/readiness-scores'),
  getVehicleTCO: (id) => fetchFromAPI(`/fleet/vehicle/${id}/tco`),
  getProcurementRecommendations: () => fetchFromAPI('/fleet/procurement-recommendations'),
  getTransitionRoadmap: () => fetchFromAPI('/fleet/transition-roadmap'),

  // Supply Chain
  getSupplyChainOverview: () => fetchFromAPI('/supply-chain/overview'),
  getSuppliers: () => fetchFromAPI('/supply-chain/suppliers'),
  getSupplyChainMap: () => fetchFromAPI('/supply-chain/map'),
  getRiskAlerts: () => fetchFromAPI('/supply-chain/risk-alerts'),
  getSupplierDetail: (id) => fetchFromAPI(`/supply-chain/supplier/${id}`),
  getTraceability: (material) => fetchFromAPI(`/supply-chain/traceability/${material}`),

  // Net Zero Carbon
  getCarbonSummary: () => fetchFromAPI('/carbon/summary'),
  getEmissions: () => fetchFromAPI('/carbon/emissions'),
  getScopeBreakdown: () => fetchFromAPI('/carbon/scope-breakdown'),
  getRouteIntensity: () => fetchFromAPI('/carbon/route-intensity'),
  getNextBestAction: () => fetchFromAPI('/carbon/next-best-action'),
  getElectrificationProgress: () => fetchFromAPI('/carbon/progress'),

  // AI Copilot
  chat: (message, module = null) => fetchFromAPI('/ai/chat', {
    method: 'POST',
    body: JSON.stringify({ message, module }),
  }),

  // Battery Passport (BPAN)
  getBpanRegistry: () => fetchFromAPI('/bpan/registry'),
  getBpanPassport: (id) => fetchFromAPI(`/bpan/passport/${id}`),
  getBpanCompliance: () => fetchFromAPI('/bpan/compliance'),
  getSecondLife: () => fetchFromAPI('/bpan/second-life'),

  // Degradation model validation
  getDegradationAccuracy: () => fetchFromAPI('/battery/degradation-accuracy'),
  getForecast: (id) => fetchFromAPI(`/battery/forecast/${id}`),

  // Multi-agent intelligence
  getAgents: () => fetchFromAPI('/intelligence/agents'),
  getCompoundRisk: () => fetchFromAPI('/intelligence/compound-risk'),
  askAgents: (query) => fetchFromAPI('/intelligence/ask', {
    method: 'POST',
    body: JSON.stringify({ query }),
  }),
};
