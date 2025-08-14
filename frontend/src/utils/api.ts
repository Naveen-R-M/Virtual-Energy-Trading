import axios from 'axios'
import dayjs from 'dayjs'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Enhanced interfaces for two-market support
export interface MarketPrice {
  node: string
  timestamp: string
  price: number
}

export interface DayAheadPrice {
  node: string
  hour_start: string
  close_price: number
}

export interface RealTimePrice {
  node: string
  timestamp: string
  price: number
}

export interface OrderRequest {
  market: 'day-ahead' | 'real-time'
  node: string
  hour_start: string
  time_slot?: string // For RT market 5-min slots
  side: 'buy' | 'sell'
  limit_price: number
  quantity_mwh: number
}

export interface Order {
  id: string
  market: 'day-ahead' | 'real-time'
  user_id: string
  node: string
  hour_start: string
  time_slot?: string
  side: 'buy' | 'sell'
  limit_price: number
  quantity_mwh: number
  status: 'pending' | 'filled' | 'rejected'
  filled_price?: number
  created_at: string
  updated_at?: string
}

export interface MatchingResult {
  order_id: string
  status: 'filled' | 'rejected'
  filled_price?: number
  filled_quantity?: number
  reason?: string
}

export interface PnLSimulation {
  node: string
  date: string
  market: 'day-ahead' | 'real-time'
  total_pnl: number
  hours: Array<{
    hour_start: string
    da_close?: number
    rt_prices: number[]
    orders: Array<{
      id: string
      side: 'buy' | 'sell'
      quantity_mwh: number
      filled_price: number
      hour_pnl: number
    }>
    hour_pnl: number
  }>
  kpis: {
    win_rate: number
    max_drawdown: number
    sharpe_ratio?: number
  }
}

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Enhanced API endpoints with two-market support
export const endpoints = {
  // Health check
  health: () => api.get('/health'),
  
  // Market data endpoints
  getDayAheadPrices: (date: string, node: string) => 
    api.get(`/api/market/da?date=${date}&node=${node}`),
  
  getRealTimePrices: (start: string, end: string, node: string) =>
    api.get(`/api/market/rt?start=${start}&end=${end}&node=${node}`),
  
  // Current market prices (for real-time trading)
  getCurrentRealTimePrice: (node: string) =>
    api.get(`/api/market/rt/current?node=${node}`),
  
  // Order management endpoints
  createOrder: (orderData: OrderRequest) => api.post('/api/orders', orderData),
  
  getOrders: (params?: { 
    date?: string
    node?: string
    market?: 'day-ahead' | 'real-time'
    status?: 'pending' | 'filled' | 'rejected'
  }) => api.get('/api/orders', { params }),
  
  deleteOrder: (orderId: string) => api.delete(`/api/orders/${orderId}`),
  
  // Day-Ahead trading operations
  matchDayAheadOrders: (date: string, node: string) =>
    api.post(`/api/orders/match/day-ahead/${date}?node=${node}`),
  
  // Real-Time trading operations
  executeRealTimeOrder: (orderId: string) =>
    api.post(`/api/orders/execute/real-time/${orderId}`),
  
  // P&L simulation endpoints
  simulateDayAheadPnL: (date: string, node: string) =>
    api.post(`/api/pnl/simulate/day-ahead/${date}?node=${node}`),
  
  simulateRealTimePnL: (date: string, node: string) =>
    api.post(`/api/pnl/simulate/real-time/${date}?node=${node}`),
  
  // Combined P&L for both markets
  getPortfolioPnL: (date: string, node: string) =>
    api.get(`/api/pnl/portfolio/${date}?node=${node}`),
  
  // Market rules and validation
  validateOrder: (orderData: OrderRequest) =>
    api.post('/api/orders/validate', orderData),
  
  getMarketStatus: (market?: 'day-ahead' | 'real-time') =>
    api.get(`/api/market/status${market ? `?market=${market}` : ''}`),
  
  // Trading limits and quotas
  getOrderQuota: (node: string, hour_start: string, market: 'day-ahead' | 'real-time', time_slot?: string) =>
    api.get(`/api/orders/quota?node=${node}&hour_start=${hour_start}&market=${market}${time_slot ? `&time_slot=${time_slot}` : ''}`),
  
  // Analytics
  getPerformanceAnalytics: (node: string, days?: number) =>
    api.get(`/api/pnl/analytics?node=${node}${days ? `&days=${days}` : ''}`),
  
  getPnLHistory: (node: string, start_date?: string, end_date?: string) =>
    api.get(`/api/pnl/history?node=${node}${start_date ? `&start_date=${start_date}` : ''}${end_date ? `&end_date=${end_date}` : ''}`)
}

// Utility functions for market operations
export const marketUtils = {
  // Check if Day-Ahead market is open
  isDayAheadMarketOpen: (): boolean => {
    const now = dayjs()
    return now.hour() < 11 // DA market closes at 11 AM
  },
  
  // Check if Real-Time market is open (always true)
  isRealTimeMarketOpen: (): boolean => {
    return true // RT market is always open
  },
  
  // Get next available trading slot for each market
  getNextTradingSlot: (market: 'day-ahead' | 'real-time') => {
    const now = dayjs()
    
    if (market === 'day-ahead') {
      if (now.hour() < 11) {
        // Same day DA trading
        return now.add(1, 'hour').startOf('hour')
      } else {
        // Next day DA trading
        return now.add(1, 'day').startOf('day').add(1, 'hour')
      }
    } else {
      // Next 5-minute RT slot
      const nextFiveMin = Math.ceil(now.minute() / 5) * 5
      return now.minute(nextFiveMin).second(0).millisecond(0)
    }
  },
  
  // Calculate time until market cutoff
  getTimeUntilCutoff: (market: 'day-ahead' | 'real-time') => {
    if (market === 'day-ahead') {
      const now = dayjs()
      const cutoff = now.set('hour', 11).set('minute', 0).set('second', 0)
      
      if (now.hour() >= 11) {
        return cutoff.add(1, 'day').diff(now, 'minute')
      }
      return cutoff.diff(now, 'minute')
    } else {
      return 0 // RT market never closes
    }
  },
  
  // Format market display names
  formatMarketName: (market: 'day-ahead' | 'real-time'): string => {
    return market === 'day-ahead' ? 'Day-Ahead' : 'Real-Time'
  },
  
  // Get market color coding
  getMarketColor: (market: 'day-ahead' | 'real-time'): string => {
    return market === 'day-ahead' ? '#007bff' : '#ff6b35'
  },
  
  // Validate order limits based on market type
  validateOrderLimits: (
    market: 'day-ahead' | 'real-time',
    timeSlot: string,
    existingOrders: Order[]
  ) => {
    const maxOrders = market === 'day-ahead' ? 10 : 50
    const slotOrders = existingOrders.filter(order => {
      if (market === 'day-ahead') {
        return order.market === 'day-ahead' && order.hour_start === timeSlot
      } else {
        return order.market === 'real-time' && order.time_slot === timeSlot
      }
    })
    
    return {
      isValid: slotOrders.length < maxOrders,
      currentCount: slotOrders.length,
      maxCount: maxOrders,
      remaining: maxOrders - slotOrders.length
    }
  }
}

export default api