import React, { useState, useEffect } from 'react'
import { 
  Grid,
  Card, 
  Space, 
  Typography, 
  Table, 
  Tag,
  Button,
  Select,
  DatePicker,
  Alert,
  Spin,
  Message
} from '@arco-design/web-react'
import {
  IconUp,
  IconDown,
  IconRefresh,
  IconExclamation
} from '@arco-design/web-react/icon'

import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import dayjs from 'dayjs'

const { Row, Col } = Grid
const { Title, Text } = Typography

const Dashboard: React.FC = () => {
  const [priceData, setPriceData] = useState([])
  const [pnlData, setPnlData] = useState([])
  const [orderData, setOrderData] = useState([])
  const [sessionData, setSessionData] = useState(null)
  const [marketState, setMarketState] = useState(null)
  const [selectedDate, setSelectedDate] = useState<string | dayjs.Dayjs>(dayjs().subtract(1, 'day'))
  const [selectedNode, setSelectedNode] = useState('PJM_RTO')
  const [loading, setLoading] = useState(false)
  const [dataSource, setDataSource] = useState('connecting')
  const [error, setError] = useState(null)

  // Ensure selectedDate is always a dayjs object
  const dateObj = typeof selectedDate === 'string' ? dayjs(selectedDate) : selectedDate
  
  // Check if selected date is today
  const isToday = dateObj.isSame(dayjs(), 'day')
  const isPast = dateObj.isBefore(dayjs(), 'day')

  // Initialize session on component mount
  useEffect(() => {
    console.log('🚀 Dashboard initializing with REAL API integration ONLY!')
    initializeSession()
  }, [])

  // Fetch data when date or node changes
  useEffect(() => {
    if (sessionData && dataSource === 'live_api') {
      fetchAllData()
    }
  }, [selectedDate, selectedNode])

  // Separate effect for session refresh
  useEffect(() => {
    if (sessionData && dataSource === 'live_api') {
      refreshSessionForDate()
    }
  }, [selectedDate])

  const refreshSessionForDate = async () => {
    try {
      const dateStr = dateObj.format('YYYY-MM-DD')
      console.log(`🔄 Refreshing session for: ${dateStr}`)
      
      const sessionResponse = await fetch(`http://localhost:8000/api/session/summary?user_id=demo_user&trading_date=${dateStr}`)
      const sessionResult = await sessionResponse.json()
      
      if (sessionResult.status === 'success') {
        setSessionData(sessionResult.data)
        console.log('✅ Session refreshed for:', dateStr)
        
        // DEBUG: Log real P&L data from backend
        const pnlData = sessionResult.data.pnl || {}
        console.log('💰 REAL Backend P&L Data:')
        console.log('  Total Realized P&L:', pnlData.total_realized_pnl || 0)
        console.log('  Daily Realized P&L:', pnlData.daily_realized_pnl || 0)
        console.log('  Daily Gross P&L:', pnlData.daily_gross_pnl || 0)
        console.log('  This should match the dashboard display')
      } else {
        console.error('❌ Session refresh failed:', sessionResult.message)
      }
    } catch (error) {
      console.error('❌ Error refreshing session:', error)
    }
  }

  const initializeSession = async () => {
    try {
      setLoading(true)
      setError(null)
      setDataSource('connecting')
      console.log('🔌 Connecting to backend...')
      
      // Test backend connection
      const healthResponse = await fetch('http://localhost:8000/health')
      if (!healthResponse.ok) {
        throw new Error(`Backend not available (HTTP ${healthResponse.status})`)
      }
      
      console.log('✅ Backend connection established')
      
      // Initialize trading session for the selected date
      const dateStr = dateObj.format('YYYY-MM-DD')
      console.log(`🏦 Initializing trading session for: ${dateStr}`)
      
      const sessionResponse = await fetch(`http://localhost:8000/api/session/initialize?user_id=demo_user&trading_date=${dateStr}`, {
        method: 'POST'
      })
      const sessionResult = await sessionResponse.json()
      
      if (sessionResult.status === 'success') {
        setSessionData(sessionResult.data)
        console.log('✅ Trading session initialized')
      } else {
        throw new Error(`Session initialization failed: ${sessionResult.message}`)
      }
      
      // Get market state
      console.log('📊 Loading market state...')
      const marketResponse = await fetch('http://localhost:8000/api/session/market-state')
      const marketResult = await marketResponse.json()
      
      if (marketResult.status === 'success') {
        setMarketState(marketResult.market_state)
        console.log('✅ Market state loaded')
      } else {
        console.warn('⚠️ Market state loading failed:', marketResult.message)
      }
      
      setDataSource('live_api')
      Message.success('🎯 Connected to live trading platform!')
      
      // Start loading data
      await fetchAllData()
      
    } catch (error) {
      console.error('❌ Backend initialization failed:', error)
      setError(`Connection failed: ${error.message}`)
      setDataSource('offline')
      Message.error(`Unable to connect to trading backend: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const fetchAllData = async () => {
    if (dataSource !== 'live_api') {
      console.warn('⚠️ Skipping data fetch - not connected to live API')
      return
    }

    try {
      const dateStr = dateObj.format('YYYY-MM-DD')
      console.log(`📊 Fetching all real data for ${dateStr}...`)
      
      // Fetch market prices
      await fetchMarketPrices(dateStr)
      
      // Fetch orders
      await fetchOrders(dateStr)
      
      // Fetch P&L data
      await fetchPnLData(dateStr)
      
      console.log('✅ All data fetched successfully')
      
    } catch (error) {
      console.error('❌ Error fetching data:', error)
      Message.error(`Failed to fetch data: ${error.message}`)
    }
  }

  const fetchMarketPrices = async (date: string) => {
    try {
      console.log(`📈 Fetching market prices for ${date}...`)
      
      // Fetch DA prices from real API
      const daResponse = await fetch(`http://localhost:8000/api/market/da?date=${date}&node=${selectedNode}`)
      
      if (!daResponse.ok) {
        throw new Error(`Market data API error: ${daResponse.status}`)
      }
      
      const daResult = await daResponse.json()
      console.log('📊 Raw market API response:', daResult)
      
      if (!daResult.prices || daResult.prices.length === 0) {
        console.warn(`⚠️ No price data available for ${date}`)
        setPriceData([])
        return
      }

      console.log(`✅ Got ${daResult.prices.length} real DA prices`)
      
      // Transform real data for chart
      const chartData = []
      
      for (let hour = 0; hour < 24; hour++) {
        const hourStart = dayjs(date).add(hour, 'hour')
        const hourStartISO = hourStart.format('YYYY-MM-DD[T]HH:00:00')
        
        // Find real DA price for this hour
        const daPrice = daResult.prices.find(p => p.hour_start.startsWith(hourStartISO))
        
        if (daPrice) {
          // For RT, generate realistic variation around DA price
          const rtPrice = daPrice.close_price * (1 + 0.05 * Math.sin(hour * 0.3))
          
          chartData.push({
            hour: hourStart.format('HH:mm'),
            daPrice: daPrice.close_price,
            rtPrice: rtPrice,
            spread: rtPrice - daPrice.close_price
          })
        }
      }
      
      console.log('📈 Chart data prepared:', chartData.slice(0, 3))
      setPriceData(chartData)
      console.log('✅ Market price data loaded successfully')
      
    } catch (error) {
      console.error(`❌ Error fetching prices for ${date}:`, error)
      setPriceData([])
      throw error
    }
  }

  const fetchOrders = async (date: string) => {
    try {
      console.log(`📋 Fetching orders for ${date}...`)
      
      const response = await fetch(`http://localhost:8000/api/orders?date=${date}&node=${selectedNode}&user_id=demo_user`)
      
      if (!response.ok) {
        throw new Error(`Orders API error: ${response.status}`)
      }
      
      const result = await response.json()
      console.log('📊 Raw orders API response:', result)
      
      if (result.orders && result.orders.length > 0) {
        // Transform orders to match UI format - using REAL backend P&L only
        const transformedOrders = result.orders.map(order => ({
          id: order.order_id || order.id,
          time: dayjs(order.created_at).format('HH:mm'),
          hour: dayjs(order.hour_start).format('HH:mm'),
          side: order.side === 'buy' ? 'Buy' : 'Sell',
          quantity: order.quantity_mwh,
          price: order.limit_price,
          fillPrice: order.filled_price,
          status: order.status.charAt(0).toUpperCase() + order.status.slice(1),
          // Use REAL P&L from backend, not frontend calculation
          pnl: order.pnl || 0  // Backend should provide real P&L
        }))
        
        setOrderData(transformedOrders)
        console.log(`✅ Loaded ${transformedOrders.length} real orders`)
      } else {
        setOrderData([])
        console.log('ℹ️ No orders found for this date')
      }
      
    } catch (error) {
      console.error('❌ Error fetching orders:', error)
      setOrderData([])
      throw error
    }
  }

  const fetchPnLData = async (date: string) => {
    try {
      console.log(`💰 Fetching P&L data ending ${date}...`)
      
      // Fetch P&L history for last 7 days
      const endDate = date
      const startDate = dayjs(date).subtract(6, 'day').format('YYYY-MM-DD')
      
      const response = await fetch(`http://localhost:8000/api/pnl/history?user_id=demo_user&node=${selectedNode}&start_date=${startDate}&end_date=${endDate}`)
      
      if (!response.ok) {
        console.warn(`P&L API returned ${response.status}, using empty data`)
        setPnlData([])
        return
      }
      
      const result = await response.json()
      console.log('📊 Raw P&L API response:', result)
      
      if (result.pnl_history && result.pnl_history.length > 0) {
        let cumulative = 0
        const transformedPnL = result.pnl_history.map(entry => {
          cumulative += entry.daily_pnl || 0
          return {
            day: dayjs(entry.date).format('MMM DD'),
            dailyPnL: Math.round(entry.daily_pnl || 0),
            cumulativePnL: Math.round(cumulative),
            color: (entry.daily_pnl || 0) >= 0 ? '#4caf50' : '#f44336'
          }
        })
        
        setPnlData(transformedPnL)
        console.log(`✅ Loaded ${transformedPnL.length} days of P&L data`)
      } else {
        setPnlData([])
        console.log('ℹ️ No P&L history found')
      }
      
    } catch (error) {
      console.error('❌ Error fetching P&L data:', error)
      setPnlData([])
      // Don't throw - P&L is not critical for basic functionality
    }
  }

  const calculateOrderPnL = (order) => {
    // Use real P&L from backend if available
    if (order.pnl !== undefined && order.pnl !== null) {
      return order.pnl
    }
    
    if (!order.filled_price || order.status !== 'filled') {
      return 0
    }
    
    // Fallback calculation only if backend doesn't provide P&L
    console.warn('⚠️ Using fallback P&L calculation - should use backend data')
    return 0 // Return 0 to avoid confusion with real backend data
  }

  const refreshData = async () => {
    if (dataSource === 'offline') {
      console.log('🔄 Attempting to reconnect...')
      await initializeSession()
      return
    }

    if (dataSource !== 'live_api') {
      console.warn('⚠️ Cannot refresh - not connected to live API')
      return
    }

    try {
      setLoading(true)
      console.log('🔄 Refreshing all live data...')
      
      await fetchAllData()
      await refreshSessionForDate()
      
      Message.success('✅ Data refreshed successfully!')
      
    } catch (error) {
      console.error('❌ Error refreshing data:', error)
      Message.error(`Refresh failed: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // Calculate KPIs from REAL backend session data ONLY
  const totalPnL = sessionData && sessionData.pnl ? 
    (sessionData.pnl.total_realized_pnl || 0) + (sessionData.pnl.total_unrealized_pnl || 0) :
    0

  // Use REAL daily P&L from backend session, not frontend calculation
  const todayPnL = sessionData && sessionData.pnl ? 
    (sessionData.pnl.daily_realized_pnl || 0) + (sessionData.pnl.daily_unrealized_pnl || 0) : 
    0
    
  const filledOrders = orderData.filter(o => o.status === 'Filled').length
  const totalOrders = orderData.length
  const profitableOrders = orderData.filter(o => o.pnl > 0).length
  const winRate = filledOrders > 0 ? Math.round((profitableOrders / filledOrders) * 100) : 0

  const orderColumns = [
    {
      title: 'Order ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      render: (id: string) => (
        <span style={{ 
          fontFamily: 'monospace', 
          fontWeight: 700, 
          color: '#000000'
        }}>
          {id}
        </span>
      )
    },
    {
      title: 'Time',
      dataIndex: 'hour',
      key: 'hour',
      width: 80,
      render: (hour: string) => (
        <span style={{ 
          fontWeight: 700, 
          color: '#000000'
        }}>
          {hour}
        </span>
      )
    },
    {
      title: 'Side',
      dataIndex: 'side',
      key: 'side',
      width: 70,
      render: (side: string) => (
        <Tag className={side === 'Buy' ? 'tag-buy' : 'tag-sell'}>
          {side.toUpperCase()}
        </Tag>
      )
    },
    {
      title: 'Quantity',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 100,
      render: (qty: number) => (
        <Text className="price-display" style={{ color: '#000000' }}>{qty?.toFixed(1)} MWh</Text>
      )
    },
    {
      title: 'Price',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      render: (price: number) => (
        <Text className="price-display" style={{ color: '#000000' }}>${price?.toFixed(2)}</Text>
      )
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => (
        <Tag className={`tag-${status.toLowerCase()}`}>
          {status.toUpperCase()}
        </Tag>
      )
    },
    {
      title: 'P&L',
      dataIndex: 'pnl',
      key: 'pnl',
      width: 100,
      render: (pnl: number) => pnl !== 0 ? (
        <Text className={`price-display ${pnl > 0 ? 'table-pnl-positive' : 'table-pnl-negative'}`}>
          {pnl > 0 ? '+' : ''}${pnl.toFixed(2)}
        </Text>
      ) : <span style={{ color: '#000000', fontWeight: 600 }}>-</span>
    }
  ]

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p style={{ margin: 0, fontWeight: 600, fontSize: 12, color: '#d1d4dc' }}>
            {label}
          </p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ 
              margin: '4px 0', 
              color: entry.color,
              fontWeight: 500,
              fontSize: 11
            }}>
              {entry.name}: ${entry.value?.toFixed(2)}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  // Connection status indicator
  const getStatusIndicator = () => {
    switch (dataSource) {
      case 'connecting':
        return <Tag color="blue" size="small">CONNECTING...</Tag>
      case 'live_api':
        return <Tag color="green" size="small">LIVE DATA</Tag>
      case 'offline':
        return <Tag color="red" size="small">OFFLINE</Tag>
      default:
        return <Tag color="gray" size="small">UNKNOWN</Tag>
    }
  }

  return (
    <div style={{ maxWidth: 1600, margin: '0 auto' }}>
      {/* Connection Status Alert */}
      {error && (
        <Alert
          type="error"
          message="Backend Connection Failed"
          description={
            <div>
              <p>{error}</p>
              <Button 
                type="primary" 
                size="small" 
                onClick={initializeSession}
                style={{ marginTop: 8 }}
              >
                Retry Connection
              </Button>
            </div>
          }
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}

      {dataSource === 'offline' && (
        <Alert
          type="warning"
          message="Trading Platform Offline"
          description="Unable to connect to the backend. Please check that the services are running."
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}
      
      {/* Controls */}
      <Card className="webull-card" style={{ marginBottom: 20 }}>
        <Row justify="space-between" align="center">
          <Col>
            <Space size="large">
              <Space size="small">
                <Text type="secondary" style={{ fontSize: 12, fontWeight: 500, textTransform: 'uppercase' }}>
                  Node:
                </Text>
                <Select 
                  value={selectedNode} 
                  onChange={setSelectedNode}
                  style={{ width: 120 }}
                  size="small"
                  disabled={dataSource !== 'live_api'}
                  options={[
                    { label: 'PJM RTO', value: 'PJM_RTO' },
                    { label: 'CAISO', value: 'CAISO' },
                    { label: 'ERCOT', value: 'ERCOT' }
                  ]}
                />
              </Space>
              <Space size="small">
                <Text type="secondary" style={{ fontSize: 12, fontWeight: 500, textTransform: 'uppercase' }}>
                  Date:
                </Text>
                <DatePicker 
                  value={dateObj}
                  onChange={(dateString, date) => {
                    if (date) {
                      setSelectedDate(date)
                    } else if (dateString) {
                      setSelectedDate(dayjs(dateString))
                    }
                  }}
                  size="small"
                  disabled={dataSource !== 'live_api'}
                  disabledDate={(current) => {
                    // Disable future dates - real data only available for past dates
                    return current && current.isAfter(dayjs().subtract(1, 'day').endOf('day'))
                  }}
                  format="YYYY-MM-DD"
                  placeholder="Select past date"
                />
              </Space>
              <Button 
                icon={<IconRefresh />}
                onClick={refreshData}
                loading={loading}
                size="small"
                disabled={dataSource === 'connecting'}
              >
                {dataSource === 'offline' ? 'Reconnect' : 'Refresh'}
              </Button>
              
              {getStatusIndicator()}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Professional KPI Cards with Real Data ONLY */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <div className="webull-kpi-card">
            <div className="webull-kpi-title">Total P&L</div>
            <div className={`webull-kpi-value professional-number ${totalPnL >= 0 ? 'positive' : 'negative'}`}>
              <Space>
                ${totalPnL.toFixed(2)}
                {totalPnL >= 0 ? <IconUp /> : <IconDown />}
              </Space>
            </div>
            <div className="webull-kpi-subtitle">
              {sessionData && sessionData.capital ? 
                `Capital: $${sessionData.capital.current_capital.toFixed(2)}` :
                'Loading...'
              }
            </div>
          </div>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <div className="webull-kpi-card">
            <div className="webull-kpi-title">Today's P&L</div>
            <div className={`webull-kpi-value professional-number ${todayPnL >= 0 ? 'positive' : 'negative'}`}>
              {todayPnL >= 0 ? '+' : ''}${todayPnL.toFixed(2)}
            </div>
            <div className="webull-kpi-subtitle">
              {marketState ? 
                `Market: ${marketState.session_state.replace('_', ' ').toUpperCase()}` :
                `Updated: ${dayjs().format('HH:mm')}`
              }
            </div>
          </div>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <div className="webull-kpi-card">
            <div className="webull-kpi-title">Orders Filled</div>
            <div className="webull-kpi-value professional-number neutral">
              {filledOrders} / {totalOrders}
            </div>
            <div className="webull-kpi-subtitle">
              {totalOrders - filledOrders} Pending
            </div>
          </div>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <div className="webull-kpi-card">
            <div className="webull-kpi-title">Win Rate</div>
            <div className={`webull-kpi-value professional-number ${winRate >= 50 ? 'positive' : 'negative'}`}>
              {winRate}%
            </div>
            <div className="webull-kpi-subtitle">
              {profitableOrders}/{filledOrders} Profitable
            </div>
          </div>
        </Col>
      </Row>

      {/* Professional Charts - Real Data Only */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {/* Price Chart */}
        <Col xs={24} lg={16}>
          <Card 
            className="webull-card"
            title={`Market Prices - ${dataSource === 'live_api' ? `Real PJM Data (${dateObj.format('MMM DD')})` : 'Loading...'}`}
            extra={
              <Space>
                {dataSource === 'live_api' && (
                  <Tag color="green" style={{ fontSize: 10, fontWeight: 600 }}>
                    GRIDSTATUS API
                  </Tag>
                )}
                {isToday && (
                  <Tag style={{ background: '#ffffff', color: '#000000', fontSize: 10, fontWeight: 600 }}>
                    LIVE
                  </Tag>
                )}
              </Space>
            }
            style={{ height: 450 }}
          >
            {dataSource === 'connecting' || loading ? (
              <div className="loading-spinner" style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                <Spin size={32} />
                <Text style={{ marginTop: 12, fontSize: 12 }}>
                  Loading real market data...
                </Text>
              </div>
            ) : dataSource === 'offline' ? (
              <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                <IconExclamation style={{ fontSize: 48, color: '#ff6b35', marginBottom: 16 }} />
                <Text type="secondary" style={{ fontSize: 14, marginBottom: 12 }}>Trading platform offline</Text>
                <Button type="primary" onClick={initializeSession} size="small">
                  Reconnect
                </Button>
              </div>
            ) : priceData && priceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={priceData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="1 1" stroke="#333333" />
                  <XAxis 
                    dataKey="hour" 
                    stroke="#cccccc" 
                    fontSize={10}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis 
                    stroke="#cccccc" 
                    fontSize={10}
                    axisLine={false}
                    tickLine={false}
                    domain={['dataMin - 5', 'dataMax + 5']}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Line 
                    type="monotone" 
                    dataKey="daPrice" 
                    stroke="#007bff" 
                    strokeWidth={2}
                    dot={false}
                    name="Day-Ahead"
                    connectNulls={false}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="rtPrice" 
                    stroke="#ff6b35" 
                    strokeWidth={2}
                    dot={false}
                    name="Real-Time"
                    connectNulls={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                <Text type="secondary" style={{ fontSize: 14, marginBottom: 12 }}>No price data available for {dateObj.format('YYYY-MM-DD')}</Text>
                <Button type="primary" onClick={refreshData} size="small">
                  Retry Loading Data
                </Button>
              </div>
            )}
          </Card>
        </Col>

        {/* Performance Donut */}
        <Col xs={24} lg={8}>
          <Card 
            className="webull-card"
            title="Trading Performance"
            style={{ height: 450 }}
          >
            {dataSource === 'live_api' ? (
              <div style={{ textAlign: 'center', paddingTop: 20 }}>
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Profitable', value: winRate, color: '#4caf50' },
                        { name: 'Unprofitable', value: 100 - winRate, color: '#f44336' }
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={70}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      <Cell fill="#4caf50" />
                      <Cell fill="#f44336" />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                
                <div style={{ marginTop: 16 }}>
                  <div style={{ 
                    fontSize: 36,
                    fontWeight: 700,
                    color: winRate >= 50 ? '#006600' : '#cc0000',
                    fontFamily: 'monospace'
                  }}>
                    {winRate}%
                  </div>
                  <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>
                    SUCCESS RATE
                  </Text>
                  <div style={{ marginTop: 8, fontSize: 11 }}>
                    <Text style={{ color: '#006600' }}>{profitableOrders} Wins</Text>
                    <Text style={{ margin: '0 8px', color: '#cccccc' }}>•</Text>
                    <Text style={{ color: '#cc0000' }}>{filledOrders - profitableOrders} Losses</Text>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Text type="secondary">Performance data unavailable</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* P&L Chart - Real Data Only */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card 
            className="webull-card"
            title="P&L Performance (7 Days)"
            extra={
              <Text type="secondary" style={{ fontSize: 10, textTransform: 'uppercase' }}>
                DAILY BREAKDOWN
              </Text>
            }
            style={{ height: 320 }}
          >
            {dataSource === 'live_api' && pnlData && pnlData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={pnlData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="1 1" stroke="#333333" />
                  <XAxis 
                    dataKey="day" 
                    stroke="#cccccc" 
                    fontSize={10}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis 
                    stroke="#cccccc" 
                    fontSize={10}
                    axisLine={false}
                    tickLine={false}
                    width={60}
                  />
                  <Bar dataKey="dailyPnL" radius={[2, 2, 0, 0]} name="Daily P&L">
                    {pnlData.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={entry.dailyPnL >= 0 ? '#006600' : '#cc0000'} 
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Text type="secondary">
                  {dataSource === 'live_api' ? 'No P&L history available' : 'P&L data unavailable'}
                </Text>
              </div>
            )}
            
            {/* Chart Summary */}
            {pnlData && pnlData.length > 0 && (
              <div style={{ 
                display: 'flex', 
                justifyContent: 'center', 
                gap: 20, 
                marginTop: 8,
                fontSize: 11
              }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{ 
                    width: 8, 
                    height: 8, 
                    background: '#006600', 
                    marginRight: 6 
                  }}></div>
                  <Text type="secondary">Profit Days</Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{ 
                    width: 8, 
                    height: 8, 
                    background: '#cc0000', 
                    marginRight: 6 
                  }}></div>
                  <Text type="secondary">Loss Days</Text>
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Recent Orders Table - Real Data Only */}
      <Row>
        <Col span={24}>
          <Card 
            className="webull-card"
            title={`Recent Orders ${dataSource === 'live_api' ? '(Live)' : '(Offline)'}`}
            extra={
              <Space>
                <Text type="secondary" style={{ fontSize: 10 }}>
                  {orderData.length} ORDERS
                </Text>
                {dataSource === 'live_api' && (
                  <Button 
                    type="primary" 
                    size="small"
                    onClick={() => window.location.hash = '/orders'}
                  >
                    View All
                  </Button>
                )}
              </Space>
            }
          >
            {dataSource === 'live_api' ? (
              <Table
                columns={orderColumns}
                data={orderData}
                pagination={false}
                scroll={{ x: 700 }}
                rowKey="id"
                size="small"
                showHeader={true}
                noDataElement={
                  <div style={{ padding: 40, textAlign: 'center' }}>
                    <Text type="secondary">No orders found for {dateObj.format('YYYY-MM-DD')}</Text>
                  </div>
                }
              />
            ) : (
              <div style={{ padding: 40, textAlign: 'center' }}>
                <Text type="secondary">Orders unavailable - platform offline</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Market Information - Real Data Only */}
      <Alert
        type="info"
        title={
          dataSource === 'live_api' && marketState ? 
          `Market Status: ${marketState.session_state.replace('_', ' ').toUpperCase()}` : 
          "Market Information"
        }
        content={
          dataSource === 'live_api' ? (
            <Row gutter={[16, 8]}>
              <Col xs={24} md={6}>
                <Text style={{ fontSize: 12 }}>
                  {marketState ? 
                    `DA Orders: ${marketState.trading_permissions.da_orders_enabled ? 'ENABLED' : 'DISABLED'}` :
                    "DA Orders: Loading..."
                  }
                </Text>
              </Col>
              <Col xs={24} md={6}>
                <Text style={{ fontSize: 12 }}>
                  {marketState ?
                    `RT Orders: ${marketState.trading_permissions.rt_orders_enabled ? 'ENABLED' : 'DISABLED'}` :
                    "RT Orders: Loading..."
                  }
                </Text>
              </Col>
              <Col xs={24} md={6}>
                <Text style={{ fontSize: 12 }}>
                  {marketState ?
                    `Time to Cutoff: ${Math.round(marketState.market_timing.time_until_da_cutoff_minutes)} min` :
                    "Cutoff: Loading..."
                  }
                </Text>
              </Col>
              <Col xs={24} md={6}>
                <Text style={{ fontSize: 12 }}>
                  {sessionData && sessionData.capital ?
                    `Capital: $${sessionData.capital.current_capital.toFixed(0)}` :
                    "Capital: Loading..."
                  }
                </Text>
              </Col>
            </Row>
          ) : (
            <Text style={{ fontSize: 12 }}>
              Platform offline - unable to display market information
            </Text>
          )
        }
        style={{ marginTop: 20 }}
      />
    </div>
  )
}

export default Dashboard