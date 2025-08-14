import dayjs from 'dayjs'

// Mock data generators for development and testing

export const generateMockDayAheadPrices = (date: string, node: string) => {
  const data = []
  const baseDate = dayjs(date)
  
  for (let i = 0; i < 24; i++) {
    const hour = baseDate.startOf('day').add(i, 'hour')
    
    // Create realistic price patterns
    let basePrice = 45
    
    // Morning ramp (6-9 AM)
    if (i >= 6 && i <= 9) {
      basePrice = 50 + (i - 6) * 5
    }
    // Afternoon peak (2-7 PM)  
    else if (i >= 14 && i <= 19) {
      basePrice = 65 + Math.sin((i - 14) / 2) * 15
    }
    // Evening decline (8-11 PM)
    else if (i >= 20 && i <= 23) {
      basePrice = 50 - (i - 20) * 3
    }
    // Off-peak hours
    else {
      basePrice = 35 + Math.random() * 10
    }
    
    // Add volatility
    const volatility = (Math.random() - 0.5) * 8
    const price = Math.max(10, basePrice + volatility)
    
    data.push({
      node,
      hour_start: hour.toISOString(),
      close_price: Math.round(price * 100) / 100
    })
  }
  
  return data
}

export const generateMockRealTimePrices = (date: string, node: string) => {
  const data = []
  const baseDate = dayjs(date)
  
  // Generate 5-minute prices for 24 hours (288 points)
  for (let i = 0; i < 288; i++) {
    const timestamp = baseDate.startOf('day').add(i * 5, 'minute')
    const hour = timestamp.hour()
    
    // Base price similar to day-ahead logic but more volatile
    let basePrice = 45
    
    if (hour >= 6 && hour <= 9) {
      basePrice = 50 + (hour - 6) * 5
    } else if (hour >= 14 && hour <= 19) {
      basePrice = 65 + Math.sin((hour - 14) / 2) * 15
    } else if (hour >= 20 && hour <= 23) {
      basePrice = 50 - (hour - 20) * 3
    } else {
      basePrice = 35 + Math.random() * 10
    }
    
    // Higher volatility for real-time
    const volatility = (Math.random() - 0.5) * 15
    const price = Math.max(5, basePrice + volatility)
    
    data.push({
      node,
      timestamp: timestamp.toISOString(),
      price: Math.round(price * 100) / 100
    })
  }
  
  return data
}

export const generateMockOrderHistory = () => {
  const orders = []
  const sides = ['buy', 'sell']
  const statuses = ['pending', 'filled', 'rejected']
  
  for (let i = 0; i < 20; i++) {
    const side = sides[Math.floor(Math.random() * sides.length)]
    const status = statuses[Math.floor(Math.random() * statuses.length)]
    const quantity = Math.round((Math.random() * 5 + 0.5) * 100) / 100
    const limitPrice = Math.round((Math.random() * 40 + 30) * 100) / 100
    const fillPrice = status === 'filled' ? 
      Math.round((limitPrice + (Math.random() - 0.5) * 5) * 100) / 100 : null
    
    let pnl = null
    if (status === 'filled' && fillPrice) {
      const rtPrice = Math.round((fillPrice + (Math.random() - 0.5) * 8) * 100) / 100
      if (side === 'buy') {
        pnl = Math.round((rtPrice - fillPrice) * quantity * 100) / 100
      } else {
        pnl = Math.round((fillPrice - rtPrice) * quantity * 100) / 100
      }
    }
    
    orders.push({
      id: `ORD-${String(i + 1).padStart(3, '0')}`,
      user_id: 'demo_user',
      node: 'PJM_RTO',
      hour_start: dayjs().startOf('day').add(Math.floor(Math.random() * 24), 'hour').toISOString(),
      side,
      limit_price: limitPrice,
      quantity_mwh: quantity,
      status,
      filled_price: fillPrice,
      pnl,
      created_at: dayjs().subtract(Math.floor(Math.random() * 24), 'hour').toISOString()
    })
  }
  
  return orders.sort((a, b) => dayjs(b.created_at).valueOf() - dayjs(a.created_at).valueOf())
}

export const calculatePnL = (orders: any[], daPrice: number, rtPrices: number[]) => {
  const rtAverage = rtPrices.reduce((sum, price) => sum + price, 0) / rtPrices.length
  
  return orders.map(order => {
    if (order.status !== 'filled') return { ...order, pnl: null }
    
    const fillPrice = order.filled_price || daPrice
    let pnl = 0
    
    if (order.side === 'buy') {
      pnl = (rtAverage - fillPrice) * order.quantity_mwh
    } else {
      pnl = (fillPrice - rtAverage) * order.quantity_mwh
    }
    
    return {
      ...order,
      pnl: Math.round(pnl * 100) / 100
    }
  })
}

export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount)
}

export const formatMWh = (amount: number): string => {
  return `${amount.toFixed(2)} MWh`
}

export const formatPrice = (price: number): string => {
  return `$${price.toFixed(2)}/MWh`
}

export const getOrderStatusColor = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'pending': return 'orange'
    case 'filled': return 'green'
    case 'rejected': return 'red'
    default: return 'blue'
  }
}

export const getSideColor = (side: string): string => {
  return side.toLowerCase() === 'buy' ? 'green' : 'red'
}

export const isMarketOpen = (): boolean => {
  const now = dayjs()
  return now.hour() < 11 // Market closes at 11 AM for next day orders
}

export const getTimeUntilCutoff = (): number => {
  const now = dayjs()
  const cutoff = now.set('hour', 11).set('minute', 0).set('second', 0)
  
  if (now.hour() >= 11) {
    // Next day cutoff
    return cutoff.add(1, 'day').diff(now, 'minute')
  }
  
  return cutoff.diff(now, 'minute')
}

export default {
  generateMockDayAheadPrices,
  generateMockRealTimePrices,
  generateMockOrderHistory,
  calculatePnL,
  formatCurrency,
  formatMWh,
  formatPrice,
  getOrderStatusColor,
  getSideColor,
  isMarketOpen,
  getTimeUntilCutoff
}
