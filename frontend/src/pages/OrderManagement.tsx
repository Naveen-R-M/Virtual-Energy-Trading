import React, { useState, useEffect } from 'react'
import {
  Grid,
  Card,
  Form,
  Select,
  InputNumber,
  Button,
  Table,
  Tag,
  Space,
  Typography,
  Alert,
  Message,
  Radio,
  DatePicker,
  Spin,
  Tooltip
} from '@arco-design/web-react'
import {
  IconRefresh,
  IconClockCircle,
  IconThunderbolt,
  IconCalendar,
  IconQuestion
} from '@arco-design/web-react/icon'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import { timezoneUtils } from '../utils/timezone'

// Configure dayjs with timezone support
dayjs.extend(utc)
dayjs.extend(timezone)

const { Row, Col } = Grid
const { Title, Text } = Typography
const FormItem = Form.Item
const RadioGroup = Radio.Group

type MarketType = 'day-ahead' | 'real-time'

interface Order {
  id: string
  market: MarketType
  hour: string
  side: 'buy' | 'sell'
  quantity: number
  limitPrice: number
  status: 'pending' | 'filled' | 'rejected' | 'awaiting_settlement' // Add new status
  fillPrice?: number
  marketPrice?: number // Settlement/Market price at execution time
  pnl?: number
  createdAt: string
  node: string
  timeSlot?: string
  settlementTime?: string // When settlement actually occurred
  timeSlotUTC?: string // UTC timestamp for calculations
  hourStartUTC?: string // UTC timestamp for calculations
}

const OrderManagement: React.FC = () => {
  const [form] = Form.useForm()
  
  // Separate states for order creation vs table filtering
  const [todayDate] = useState(dayjs()) // For new orders - always TODAY (locked)
  const [tableFilterDate, setTableFilterDate] = useState(dayjs().subtract(1, 'day')) // For table filtering
  
  const [selectedNode, setSelectedNode] = useState('PJM_RTO')
  const [selectedMarket, setSelectedMarket] = useState<MarketType>('real-time')
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(false)
  const [rtCountdown, setRtCountdown] = useState<string>('')
  
  // Filter states
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterMarket, setFilterMarket] = useState<string>('all')
  
  // Session data
  const [sessionData, setSessionData] = useState(null)
  const [marketState, setMarketState] = useState(null)
  const [dataSource, setDataSource] = useState('connecting')

  // Market state helpers
  const isDATradingOpen = () => {
    const now = dayjs()
    const cutoff = now.startOf('day').add(11, 'hour') // 11:00 AM today
    return now.isBefore(cutoff)
  }

  const isRTMarketOpen = () => {
    // RT market is ALWAYS open for next 5-minute slots, 24/7
    return true
  }

  // Initialize session
  useEffect(() => {
    initializeSession()
  }, [])

  // Fetch orders when table filter date changes
  useEffect(() => {
    if (dataSource === 'real_api') {
      fetchOrdersForDate(tableFilterDate.format('YYYY-MM-DD'))
    }
  }, [tableFilterDate, selectedNode, dataSource])

  const getSettlementPrice = async (hourStart: string, timeSlot?: string) => {
    try {
      // For RT orders, fetch the actual RT price for that 5-minute interval
      const slotTime = timeSlot || hourStart
      
      // Query RT prices from the backend for this specific interval
      const response = await fetch(
        `http://localhost:8000/api/market/rt?start=${slotTime}&end=${slotTime}&node=${selectedNode}`
      )
      
      if (response.ok) {
        const rtData = await response.json()
        if (rtData.prices && rtData.prices.length > 0) {
          const settlementPrice = rtData.prices[0].price
          console.log(`🏦 Real settlement price for ${slotTime}: ${settlementPrice}`)
          return settlementPrice
        }
      }
      
      console.warn(`⚠️ No RT price data for ${slotTime}, using fallback`)
      // Fallback to time-based estimation if no real data
      const timeHour = dayjs(hourStart).hour()
      if (timeHour >= 18 && timeHour <= 20) {
        return 42.26 // Peak evening hours
      } else if (timeHour >= 14 && timeHour <= 17) {
        return 41.85 // Afternoon hours  
      } else {
        return 41.50 // Off-peak hours
      }
      
    } catch (error) {
      console.error('Error fetching settlement price:', error)
      return 42.26 // Safe fallback
    }
  }

  // RT countdown timer + settlement checker
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date()
      const nextSlot = new Date(now)
      nextSlot.setMinutes(Math.ceil(now.getMinutes() / 5) * 5, 0, 0)
      
      const diff = nextSlot.getTime() - now.getTime()
      const minutes = Math.floor(diff / 60000)
      const seconds = Math.floor((diff % 60000) / 1000)
      
      setRtCountdown(`${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`)
      
      // Check for RT orders ready for settlement (every 30 seconds)
      if (seconds % 30 === 0) {
        checkPendingRTSettlements()
      }
    }, 1000)
    
    return () => clearInterval(interval)
  }, [])

  const checkPendingRTSettlements = async () => {
    if (dataSource !== 'real_api') return
    
    // Find RT orders that are past their execution time but still pending
    const now = dayjs()
    const pendingRTOrders = orders.filter(order => {
      if (order.market !== 'real-time' || order.status !== 'pending') {
        return false
      }
      
      // Use UTC timestamp for comparison
      const executionTimeUTC = order.timeSlotUTC || order.hourStartUTC
      if (!executionTimeUTC) return false
      
      const executionTime = dayjs(executionTimeUTC)
      const settlementTime = executionTime.add(5, 'minute').add(30, 'second')
      
      // Check if settlement time has passed
      return now.isAfter(settlementTime)
    })
    
    if (pendingRTOrders.length > 0) {
      console.log(`🔄 Checking settlement for ${pendingRTOrders.length} pending RT orders...`)
      
      // Trigger settlement check on backend
      try {
        const response = await fetch(
          `http://localhost:8000/api/orders/settle-rt?user_id=demo_user&node=${selectedNode}`,
          { method: 'POST' }
        )
        
        if (response.ok) {
          console.log('✅ RT settlement check triggered')
          // Refresh orders to show updated statuses
          await fetchOrdersForDate(tableFilterDate.format('YYYY-MM-DD'))
        }
      } catch (error) {
        console.error('Error triggering RT settlement:', error)
      }
    }
  }

  const initializeSession = async () => {
    try {
      setDataSource('connecting')
      
      // Test backend connection
      const healthResponse = await fetch('http://localhost:8000/health')
      if (!healthResponse.ok) {
        throw new Error('Backend not available')
      }
      
      // Initialize session for TODAY (not table filter date)
      const todayStr = todayDate.format('YYYY-MM-DD')
      const sessionResponse = await fetch(
        `http://localhost:8000/api/session/initialize?user_id=demo_user&trading_date=${todayStr}`, 
        { method: 'POST' }
      )
      const sessionResult = await sessionResponse.json()
      
      if (sessionResult.status === 'success') {
        setSessionData(sessionResult.data)
      }
      
      // Get market state
      const marketResponse = await fetch('http://localhost:8000/api/session/market-state')
      const marketResult = await marketResponse.json()
      
      if (marketResult.status === 'success') {
        setMarketState(marketResult.market_state)
      }
      
      setDataSource('real_api')
      Message.success('Connected to live trading platform!')
      
    } catch (error) {
      console.error('Failed to initialize:', error)
      setDataSource('offline')
      Message.error('Unable to connect to backend')
    }
  }

  const fetchOrdersForDate = async (dateStr: string) => {
    try {
      setLoading(true)
      console.log(`📋 Fetching orders for ${dateStr}...`)
      
      const response = await fetch(
        `http://localhost:8000/api/orders/?date=${dateStr}&node=${selectedNode}&user_id=demo_user`
      )
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }
      
      const result = await response.json()
      
      if (result.orders && result.orders.length > 0) {
        // Transform orders with real settlement prices
        const transformedOrders = await Promise.all(
          result.orders.map(async (order) => {
            const settlementPrice = order.filled_price ? 
              await getSettlementPrice(order.hour_start, order.time_slot) : 
              undefined
            
            // Convert UTC times to EDT for display
            // Parse as UTC first, then convert to EDT
            const hourStartEDT = dayjs.utc(order.hour_start).tz('America/New_York')
            const timeSlotEDT = order.time_slot_utc ? 
              dayjs.utc(order.time_slot_utc).tz('America/New_York') : undefined
            
            // Debug logging for RT orders
            if (order.market === 'real-time' && order.time_slot_utc) {
              console.log('🕐 RT Time Conversion:', {
                utcFromBackend: order.time_slot_utc,
                edtForDisplay: timeSlotEDT?.format('HH:mm [EDT]'),
                fullEDT: timeSlotEDT?.format('YYYY-MM-DD HH:mm:ss [EDT]')
              })
            }
              
            return {
              id: order.order_id || order.id,
              market: order.market || 'day-ahead',
              hour: hourStartEDT.format('HH:mm'),  // Now in EDT
              side: order.side === 'buy' ? 'buy' : 'sell',
              quantity: order.quantity_mwh,
              limitPrice: order.limit_price,
              status: order.status,
              fillPrice: order.filled_price,
              marketPrice: settlementPrice,
              pnl: order.pnl || order.filled_price ? calculateRealPnL(order) : 0,
              createdAt: order.created_at,
              node: order.node,
              timeSlot: timeSlotEDT ? timeSlotEDT.format('HH:mm') : undefined,  // Now in EDT
              timeSlotUTC: order.time_slot_utc,  // Keep UTC for calculations
              hourStartUTC: order.hour_start     // Keep UTC for calculations
            }
          })
        )
        
        setOrders(transformedOrders)
        console.log(`✅ Loaded ${transformedOrders.length} orders for ${dateStr}`)
      } else {
        setOrders([])
        console.log('ℹ️ No orders found for this date')
      }
      
    } catch (error) {
      console.error('Error fetching orders:', error)
      setOrders([])
    } finally {
      setLoading(false)
    }
  }

  const calculateRealPnL = (order) => {
    if (!order.filled_price || order.status !== 'filled') {
      return 0
    }
    
    // PJM Settlement Logic:
    // P&L = (Settlement Price - Fill Price) * Quantity * Side
    
    const fillPrice = order.filled_price // Price you actually paid/received (LMP)
    const quantity = order.quantity_mwh
    const side = order.side
    
    // Use real settlement price from order object (fetched from API)
    const settlementPrice = order.marketPrice || getSettlementPriceFallback(order.hour_start)
    
    let pnl = 0
    
    if (side === 'buy') {
      // BUY P&L: (Settlement Price - Fill Price) * Quantity
      // If settlement > fill → profit (energy worth more than you paid)
      pnl = (settlementPrice - fillPrice) * quantity
    } else {
      // SELL P&L: (Fill Price - Settlement Price) * Quantity  
      // If fill > settlement → profit (you got more than market rate)
      pnl = (fillPrice - settlementPrice) * quantity
    }
    
    console.log(`🏦 PJM Settlement P&L for ${side}: (${side === 'buy' ? settlementPrice + '-' + fillPrice : fillPrice + '-' + settlementPrice}) * ${quantity} = ${pnl.toFixed(2)}`)
    
    return Math.round(pnl * 100) / 100
  }

  const getSettlementPriceFallback = (hourStart: string) => {
    // Fallback settlement price calculation when API data unavailable
    const timeHour = dayjs(hourStart).hour()
    
    if (timeHour >= 18 && timeHour <= 20) {
      return 42.26 // Peak evening hours
    } else if (timeHour >= 14 && timeHour <= 17) {
      return 41.85 // Afternoon hours  
    } else {
      return 41.50 // Off-peak hours
    }
  }

  const handleCreateOrder = async (values: any) => {
    try {
      setLoading(true)
      
      // NEW ORDERS ALWAYS GO TO TODAY regardless of table filter
      const todayStr = todayDate.format('YYYY-MM-DD')
      
      let hourStartUtc
      let timeSlotUtc
      let settlementInfo = ''
      
      if (selectedMarket === 'day-ahead') {
        // For DA market, convert EDT hour to UTC
        hourStartUtc = timezoneUtils.formatDAHour(todayStr, values.hour)
      } else {
        // Parse RT interval (e.g., "20:45-20:50")
        const intervalParts = values.timeSlot.split('-')
        const startTime = intervalParts[0].trim() // "20:45"
        const endTime = intervalParts[1].trim()   // "20:50"
        
        // Convert RT times from EDT to UTC using our timezone utility
        const rtSlot = timezoneUtils.formatRTTimeSlot(todayStr, startTime)
        hourStartUtc = rtSlot.hourStartUtc
        timeSlotUtc = rtSlot.timeSlotUtc
        
        // Calculate settlement timing in EDT for display
        const edtEnd = dayjs.tz(`${todayStr} ${endTime}`, 'America/New_York')
        const settlementTime = edtEnd.add(30, 'second')
        settlementInfo = `Settlement expected at ${settlementTime.format('HH:mm:ss')} EDT`
        
        // Debug: Log the conversion
        console.log('🕐 Time conversion:', {
          userSelected: `${startTime} EDT`,
          sentToAPI: timeSlotUtc,
          debug: timezoneUtils.debugTimeConversion(todayStr, startTime)
        })
      }
      
      const orderData = {
        hour_start: hourStartUtc,
        node: selectedNode,
        market: selectedMarket,
        side: values.side,
        order_type: 'LMT',
        limit_price: Number(values.limitPrice),
        quantity_mwh: Number(values.quantity),
        time_in_force: 'GTC'
      }
      
      // Add time_slot for RT orders
      if (selectedMarket === 'real-time') {
        orderData.time_slot = timeSlotUtc
      }
      
      console.log('📝 Creating NEW order for TODAY:', orderData)
      
      const response = await fetch('http://localhost:8000/api/orders?user_id=demo_user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData)
      })
      
      if (response.ok) {
        const result = await response.json()
        
        if (selectedMarket === 'real-time') {
          Message.success({
            content: (
              <div>
                <div>✅ RT Order submitted for {values.timeSlot} interval!</div>
                <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                  {settlementInfo || 'Will settle when RT price data is available'}
                </div>
              </div>
            ),
            duration: 6
          })
        } else {
          Message.success('✅ DA Order placed successfully!')
        }
        
        form.resetFields()
        
        // If table is showing today, refresh it to show the new order
        if (tableFilterDate.isSame(todayDate, 'day')) {
          await fetchOrdersForDate(todayStr)
        }
      } else {
        const errorData = await response.json()
        Message.error(`❌ Order failed: ${errorData.detail || 'Unknown error'}`)
      }
      
    } catch (error) {
      console.error('Error creating order:', error)
      Message.error('Order creation failed')
    } finally {
      setLoading(false)
    }
  }

  const getNextRTSlots = () => {
    const now = new Date()
    const slots = []
    
    // Current 5-minute interval boundaries
    const currentMinute = now.getMinutes()
    const currentIntervalStart = Math.floor(currentMinute / 5) * 5
    const currentIntervalEnd = currentIntervalStart + 5
    
    // Check if current interval is still open for orders
    const minutesUntilCurrentEnd = currentIntervalEnd - currentMinute
    const secondsUntilCurrentEnd = minutesUntilCurrentEnd * 60 - now.getSeconds()
    
    let startFromInterval = 0
    
    // If less than 30 seconds until current interval ends, skip to next
    if (secondsUntilCurrentEnd < 30) {
      startFromInterval = 1 // Skip current interval, start from next
    }
    
    for (let i = startFromInterval; i < startFromInterval + 12; i++) {
      const intervalStart = new Date(now)
      intervalStart.setMinutes(currentIntervalStart + (i * 5), 0, 0)
      
      const intervalEnd = new Date(intervalStart)
      intervalEnd.setMinutes(intervalStart.getMinutes() + 5)
      
      const settlementTime = new Date(intervalEnd)
      settlementTime.setSeconds(30) // Settlement published ~30s after interval end
      
      const timeStr = intervalStart.toTimeString().slice(0, 5)
      const endTimeStr = intervalEnd.toTimeString().slice(0, 5)
      
      // Calculate time until interval end for order cutoff
      const timeUntilEnd = intervalEnd.getTime() - now.getTime()
      const minutesUntilEnd = Math.floor(timeUntilEnd / 60000)
      const secondsUntilEnd = Math.floor((timeUntilEnd % 60000) / 1000)
      
      let label, disabled = false
      
      if (i === 0 && startFromInterval === 0) {
        // Current interval still open
        label = (
          <div>
            <Text style={{ fontWeight: 600 }}>{timeStr}-{endTimeStr}</Text>
            <div style={{ fontSize: 9, color: '#52c41a' }}>
              Closes in {String(minutesUntilEnd).padStart(2, '0')}:{String(secondsUntilEnd).padStart(2, '0')}
            </div>
          </div>
        )
      } else {
        // Future intervals
        const settlementDelay = Math.floor((settlementTime.getTime() - now.getTime()) / 60000)
        label = (
          <div>
            <Text style={{ fontWeight: 600 }}>{timeStr}-{endTimeStr}</Text>
            <div style={{ fontSize: 9, color: '#888' }}>
              Settlement in ~{settlementDelay}min
            </div>
          </div>
        )
      }
      
      slots.push({
        value: `${timeStr}-${endTimeStr}`,
        label: label,
        disabled: disabled,
        intervalStart: intervalStart.toISOString(),
        intervalEnd: intervalEnd.toISOString(),
        settlementTime: settlementTime.toISOString()
      })
    }
    
    return slots
  }

  const getDayAheadHours = () => {
    const hours = []
    for (let i = 0; i < 24; i++) {
      const hourStr = String(i).padStart(2, '0') + ':00'
      hours.push({
        value: hourStr,
        label: hourStr,
        disabled: false
      })
    }
    return hours
  }

  const filteredOrders = orders.filter(order => {
    const statusMatch = filterStatus === 'all' || order.status === filterStatus
    const marketMatch = filterMarket === 'all' || order.market === filterMarket
    return statusMatch && marketMatch
  })

  // Calculate REAL today's P&L from actual filled orders
  const calculateTodaysPnL = () => {
    const filledOrders = orders.filter(o => o.status === 'filled')
    return filledOrders.reduce((total, order) => total + (order.pnl || 0), 0)
  }

  const todaysPnLCalculated = calculateTodaysPnL()

  const orderColumns = [
    {
      title: 'Order ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
      render: (id: string) => (
        <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#000000', fontSize: 11 }}>
          {id.substring(0, 8)}...
        </span>
      )
    },
    {
      title: 'Market',
      dataIndex: 'market',
      key: 'market',
      width: 90,
      render: (market: MarketType) => (
        <Tag color={market === 'day-ahead' ? 'blue' : 'orange'} size="small">
          {market === 'day-ahead' ? 'DA' : 'RT'}
        </Tag>
      )
    },
    {
      title: 'Time',
      dataIndex: 'hour',
      key: 'hour',
      width: 90,
      render: (hour: string, record: Order) => (
        <div>
          <span style={{ fontWeight: 700, color: '#000000' }}>
            {hour}
          </span>
          {record.timeSlot && record.market === 'real-time' && (
            <div style={{ fontSize: 9, color: '#000000' }}>Slot: {record.timeSlot}</div>
          )}
        </div>
      )
    },
    {
      title: 'Side',
      dataIndex: 'side',
      key: 'side',
      width: 70,
      render: (side: string) => (
        <Tag className={side === 'buy' ? 'tag-buy' : 'tag-sell'}>
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
        <Text style={{ color: '#000000', fontWeight: 600 }}>{qty?.toFixed(1)} MWh</Text>
      )
    },
    {
      title: 'Limit Price',
      dataIndex: 'limitPrice',
      key: 'limitPrice',
      width: 100,
      render: (price: number) => (
        <Text style={{ color: '#000000', fontWeight: 600 }}>${price?.toFixed(2)}</Text>
      )
    },
    {
      title: 'Fill Price',
      dataIndex: 'fillPrice',
      key: 'fillPrice',
      width: 100,
      render: (price?: number) =>
        typeof price === 'number' ? (
          <Text style={{ color: '#000000' }}>${price.toFixed(2)}</Text>
        ) : (
          <span style={{ color: '#000000', fontWeight: 600 }}>—</span>
        )
    },
    {
      title: (
        <Space>
          <span>Market Price</span>
          <Tooltip content="The settlement LMP (Locational Marginal Price) used for P&L calculation">
            <IconQuestion style={{ fontSize: 12, color: '#888' }} />
          </Tooltip>
        </Space>
      ),
      dataIndex: 'marketPrice',
      key: 'marketPrice',
      width: 110,
      render: (price?: number, record: Order) => {
        if (record.status !== 'filled') {
          return <span style={{ color: '#000000' }}>—</span>
        }
        return typeof price === 'number' ? (
          <div>
            <Text style={{ color: '#4169E1', fontWeight: 600 }}>${price.toFixed(2)}</Text>
            <div style={{ fontSize: 9, color: '#000000' }}>RT LMP</div>
          </div>
        ) : (
          <div>
            <Text style={{ color: '#888' }}>—</Text>
            <div style={{ fontSize: 9, color: '#000000' }}>No data</div>
          </div>
        )
      }
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string, record: Order) => {
        const now = dayjs()
        
        // Enhanced status for RT orders with timing
        if (record.market === 'real-time' && status === 'pending') {
          // Use UTC timestamp if available, then convert to EDT for display
          const utcTime = record.timeSlotUTC || record.hourStartUTC
          if (utcTime) {
            // Parse as UTC explicitly, then convert to EDT for display
            const executionTimeUTC = dayjs.utc(utcTime)
            const executionTimeEDT = executionTimeUTC.tz('America/New_York')
            const settlementTime = executionTimeUTC.add(5, 'minute').add(30, 'second')
            
            if (now.isBefore(executionTimeUTC)) {
              return (
                <div>
                  <Tag color="orange" size="small">PENDING</Tag>
                  <div style={{ fontSize: 9, color: '#888' }}>Executes: {executionTimeEDT.format('HH:mm')} EDT</div>
                </div>
              )
            } else if (now.isBefore(settlementTime)) {
              return (
                <div>
                  <Tag color="blue" size="small">EXECUTING</Tag>
                  <div style={{ fontSize: 9, color: '#888' }}>Awaiting RT data...</div>
                </div>
              )
            } else {
              return (
                <div>
                  <Tag color="purple" size="small">SETTLING</Tag>
                  <div style={{ fontSize: 9, color: '#888' }}>Processing...</div>
                </div>
              )
            }
          }
        }
        
        // Standard status display
        let color = 'blue'
        let text = status.toUpperCase()
        
        switch (status.toLowerCase()) {
          case 'filled':
            color = 'green'
            break
          case 'rejected':
            color = 'red'
            break
          case 'pending':
            color = 'orange'
            break
          default:
            color = 'blue'
        }
        
        return (
          <Tag color={color} size="small">
            {text}
          </Tag>
        )
      }
    },
    {
      title: 'P&L',
      dataIndex: 'pnl',
      key: 'pnl',
      width: 100,
      render: (pnl?: number) =>
        pnl && pnl !== 0 ? (
          <Text className={`${pnl > 0 ? 'table-pnl-positive' : 'table-pnl-negative'}`}>
            {pnl > 0 ? '+' : ''}${pnl.toFixed(2)}
          </Text>
        ) : (
          <span style={{ color: '#000000' }}>—</span>
        )
    }
  ]

  return (
    <div style={{ maxWidth: 1600, margin: '0 auto' }}>
      {/* Header - NO DATE PICKER HERE */}
      <Card className="webull-card" style={{ marginBottom: 20 }}>
        <Row justify="space-between" align="center">
          <Col>
            <div>
              <Title level={3} style={{ margin: 0, color: '#ffffff' }}>
                Order Management
              </Title>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Create orders for TODAY • View history by date
              </Text>
            </div>
          </Col>
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
                  options={[
                    { label: 'PJM RTO', value: 'PJM_RTO' },
                    { label: 'CAISO', value: 'CAISO' },
                    { label: 'ERCOT', value: 'ERCOT' }
                  ]}
                />
              </Space>

              <Button 
                icon={<IconRefresh />} 
                onClick={() => fetchOrdersForDate(tableFilterDate.format('YYYY-MM-DD'))} 
                loading={loading} 
                size="small"
              >
                Refresh
              </Button>

              <Tag color="green" size="small">LIVE DATA</Tag>
            </Space>
          </Col>
        </Row>
      </Card>

      <Row gutter={[24, 24]}>
        {/* Create New Order - Always for TODAY */}
        <Col xs={24} lg={10}>
          <Card className="webull-card" title={`Create New Order - ${todayDate.format('MMM DD, YYYY')}`}>
            <Form form={form} layout="vertical" onSubmit={handleCreateOrder}>
              
              {/* Market Type Selection */}
              <FormItem label="Market Type">
                <RadioGroup value={selectedMarket} onChange={setSelectedMarket} style={{ width: '100%' }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Radio
                      value="day-ahead"
                      disabled={!isDATradingOpen()}
                      style={{
                        padding: '12px 16px',
                        border: '1px solid #333',
                        borderRadius: '6px',
                        margin: 0,
                        width: '100%',
                        background: selectedMarket === 'day-ahead' ? 'rgba(0, 123, 255, 0.1)' : 'transparent'
                      }}
                    >
                      <Space>
                        <IconCalendar />
                        <div>
                          <div style={{ fontWeight: 600 }}>Day-Ahead Market</div>
                          <Text style={{ fontSize: 11, color: '#888' }}>
                            Hourly delivery, 11 AM cutoff
                            <Tag 
                              color={isDATradingOpen() ? 'green' : 'red'} 
                              size="small" 
                              style={{ marginLeft: 8 }}
                            >
                              {isDATradingOpen() ? 'OPEN' : 'CLOSED'}
                            </Tag>
                          </Text>
                        </div>
                      </Space>
                    </Radio>

                    <Radio
                      value="real-time"
                      disabled={false} // RT always enabled
                      style={{
                        padding: '12px 16px',
                        border: '1px solid #333',
                        borderRadius: '6px',
                        margin: 0,
                        width: '100%',
                        background: selectedMarket === 'real-time' ? 'rgba(255, 107, 53, 0.1)' : 'transparent'
                      }}
                    >
                      <Space>
                        <IconThunderbolt />
                        <div>
                          <div style={{ fontWeight: 600 }}>Real-Time Market</div>
                          <Text style={{ fontSize: 11, color: '#888' }}>
                            5-minute execution, next slot: {rtCountdown}
                            <Tag color="green" size="small" style={{ marginLeft: 8 }}>
                              OPEN
                            </Tag>
                          </Text>
                        </div>
                      </Space>
                    </Radio>
                  </Space>
                </RadioGroup>
              </FormItem>

              {/* Order Side */}
              <FormItem label="Order Side" field="side" rules={[{ required: true }]}>
                <RadioGroup>
                  <Radio value="buy">
                    <Tag className="tag-buy" style={{ minWidth: 60, textAlign: 'center' }}>BUY</Tag>
                  </Radio>
                  <Radio value="sell">
                    <Tag className="tag-sell" style={{ minWidth: 60, textAlign: 'center' }}>SELL</Tag>
                  </Radio>
                </RadioGroup>
              </FormItem>

              {/* Quantity */}
              <FormItem 
                label="Quantity (MWh)" 
                field="quantity"
                rules={[
                  { required: true, message: 'Quantity is required' },
                  { type: 'number', min: 0.1, max: 100, message: 'Quantity must be between 0.1 and 100 MWh' }
                ]}
              >
                <InputNumber 
                  placeholder="Enter quantity" 
                  min={0.1} 
                  max={100} 
                  step={0.1} 
                  precision={1} 
                  style={{ width: '100%' }} 
                />
              </FormItem>

              {/* Limit Price */}
              <FormItem 
                label="Limit Price ($/MWh)" 
                field="limitPrice"
                rules={[
                  { required: true, message: 'Limit price is required' },
                  { type: 'number', min: 0, message: 'Price must be positive' }
                ]}
                extra={
                  <Text style={{ fontSize: 11, color: '#888' }}>
                    💡 BUY: Set above market price to ensure fill • SELL: Set below market price to ensure fill
                  </Text>
                }
              >
                <InputNumber 
                  placeholder="Enter limit price" 
                  min={0} 
                  step={0.01} 
                  precision={2} 
                  style={{ width: '100%' }} 
                />
              </FormItem>

              {/* Day-Ahead Hour Selection */}
              {selectedMarket === 'day-ahead' && (
                <FormItem 
                  label="Delivery Hour" 
                  field="hour"
                  rules={[{ required: true, message: 'Delivery hour is required' }]}
                >
                  <Select
                    placeholder="Select delivery hour"
                    options={getDayAheadHours()}
                  />
                </FormItem>
              )}

              {/* Real-Time Interval Selection */}
              {selectedMarket === 'real-time' && (
                <FormItem 
                  label={
                    <Space>
                      <span>5-Minute Interval</span>
                      <IconClockCircle style={{ color: '#52c41a' }} />
                      <Text style={{ fontSize: 10, color: '#52c41a' }}>Live Intervals</Text>
                    </Space>
                  }
                  field="timeSlot"
                  rules={[{ required: true, message: 'Interval is required' }]}
                  extra={
                    <Text style={{ fontSize: 11, color: '#888' }}>
                      🏦 Order cutoff: 30s before interval end • Settlement: ~30s after interval end • RT data from GridStatus API
                    </Text>
                  }
                >
                  <Select
                    placeholder="Select 5-minute execution slot"
                    options={getNextRTSlots()}
                  />
                </FormItem>
              )}

              <FormItem>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  long
                  disabled={selectedMarket === 'day-ahead' && !isDATradingOpen()}
                  style={{
                    background: selectedMarket === 'day-ahead' ? '#007bff' : '#ff6b35',
                    borderColor: selectedMarket === 'day-ahead' ? '#007bff' : '#ff6b35'
                  }}
                >
                  {selectedMarket === 'day-ahead' ? 'Submit DA Order' : 'Execute RT Order'}
                </Button>
              </FormItem>
            </Form>
          </Card>
        </Col>

        {/* Orders Table with Date Filter */}
        <Col xs={24} lg={14}>
          <Card
            className="webull-card"
            title={
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <span>Orders History</span>
                  <Tag color="blue" size="small" style={{ marginLeft: 8 }}>
                    LIVE
                  </Tag>
                </div>
                
                {/* DATE FILTER MOVED HERE */}
                <Space>
                  <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>
                    Filter Date:
                  </Text>
                  <DatePicker
                    value={tableFilterDate}
                    onChange={(dateString, date) => {
                      if (date) {
                        setTableFilterDate(date)
                        console.log(`📅 Table filter changed to: ${date.format('YYYY-MM-DD')}`)
                      }
                    }}
                    size="small"
                    disabledDate={(current) => {
                      // Allow past dates and today, disable future dates
                      return current && current.isAfter(dayjs().endOf('day'))
                    }}
                    format="YYYY-MM-DD"
                    placeholder="Select date"
                  />
                </Space>
              </div>
            }
            extra={
              <Space>
                <Select
                  value={filterMarket}
                  onChange={setFilterMarket}
                  style={{ width: 120 }}
                  size="small"
                  options={[
                    { label: 'All Markets', value: 'all' },
                    { label: 'Day-Ahead', value: 'day-ahead' },
                    { label: 'Real-Time', value: 'real-time' }
                  ]}
                />
                <Select
                  value={filterStatus}
                  onChange={setFilterStatus}
                  style={{ width: 100 }}
                  size="small"
                  options={[
                    { label: 'All Status', value: 'all' },
                    { label: 'Pending', value: 'pending' },
                    { label: 'Filled', value: 'filled' },
                    { label: 'Rejected', value: 'rejected' }
                  ]}
                />
                <Text type="secondary" style={{ fontSize: 10 }}>
                  {filteredOrders.length} ORDERS
                </Text>
              </Space>
            }
          >
            {loading ? (
              <div style={{ textAlign: 'center', padding: 60 }}>
                <Spin size={32} />
                <Text style={{ color: '#cccccc', marginTop: 16 }}>
                  Loading orders for {tableFilterDate.format('MMM DD, YYYY')}...
                </Text>
              </div>
            ) : (
              <Table
                columns={orderColumns}
                data={filteredOrders}
                pagination={{
                  pageSize: 10,
                  showTotal: (total, range) => (
                    <Text style={{ fontSize: 11, color: '#888' }}>
                      {range[0]}-{range[1]} of {total} orders on {tableFilterDate.format('MMM DD, YYYY')}
                    </Text>
                  )
                }}
                scroll={{ x: 1200 }}
                rowKey="id"
                size="small"
                showHeader={true}
                noDataElement={
                  <div style={{ textAlign: 'center', padding: 40 }}>
                    <Text type="secondary">
                      No orders found for {tableFilterDate.format('MMM DD, YYYY')}
                    </Text>
                    <div style={{ marginTop: 8 }}>
                      <Button 
                        type="primary" 
                        size="small"
                        onClick={() => setTableFilterDate(dayjs().subtract(1, 'day'))}
                      >
                        View August 14 Orders
                      </Button>
                    </div>
                  </div>
                }
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* Session Summary */}
      {sessionData && (
        <Card className="webull-card" title="Session Summary" style={{ marginTop: 24 }}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={6}>
              <Text strong style={{ color: '#cccccc' }}>Capital: </Text>
              <Text style={{ color: '#ffffff', fontWeight: 600 }}>
                ${sessionData.capital?.current_capital?.toFixed(2) || '0.00'}
              </Text>
            </Col>
            <Col xs={24} sm={6}>
              <Text strong style={{ color: '#cccccc' }}>Today's P&L: </Text>
              <Text style={{ color: todaysPnLCalculated >= 0 ? '#00ff00' : '#ff0000', fontWeight: 600 }}>
                {todaysPnLCalculated >= 0 ? '+' : ''}${todaysPnLCalculated.toFixed(2)}
              </Text>
              <Text style={{ fontSize: 10, color: '#888', display: 'block' }}>
                (Calculated from orders)
              </Text>
            </Col>
            <Col xs={24} sm={6}>
              <Text strong style={{ color: '#cccccc' }}>Backend P&L: </Text>
              <Text style={{ color: '#ffffff', fontWeight: 600 }}>
                ${((sessionData.pnl?.total_realized_pnl || 0) + (sessionData.pnl?.total_unrealized_pnl || 0)).toFixed(2)}
              </Text>
              <Text style={{ fontSize: 10, color: '#888', display: 'block' }}>
                (Backend calculation)
              </Text>
            </Col>
            <Col xs={24} sm={6}>
              <Text strong style={{ color: '#cccccc' }}>Viewing: </Text>
              <Text style={{ color: '#ffffff', fontWeight: 600 }}>
                {tableFilterDate.format('MMM DD, YYYY')}
              </Text>
            </Col>
            <Col xs={24} sm={6}>
              <Text strong style={{ color: '#cccccc' }}>Orders Shown: </Text>
              <Text style={{ color: '#ffffff', fontWeight: 600 }}>
                {filteredOrders.length}
              </Text>
            </Col>
          </Row>
        </Card>
      )}
      
      {/* Real-Time Settlement Info */}
      <Alert
        type="info"
        title="Real-Time Settlement Process"
        content={
          <Row gutter={[16, 8]}>
            <Col xs={24} md={6}>
              <Text style={{ fontSize: 12 }}>
                🕒 RT Order → PENDING (awaiting execution)
              </Text>
            </Col>
            <Col xs={24} md={6}>
              <Text style={{ fontSize: 12 }}>
                ⚡ Execution Time → EXECUTING (awaiting RT data)
              </Text>
            </Col>
            <Col xs={24} md={6}>
              <Text style={{ fontSize: 12 }}>
                🏦 RT Data Available → SETTLING (processing)
              </Text>
            </Col>
            <Col xs={24} md={6}>
              <Text style={{ fontSize: 12 }}>
                ✅ Settlement Complete → FILLED/REJECTED
              </Text>
            </Col>
          </Row>
        }
        style={{ marginTop: 20 }}
      />
      
      {/* Trading Rules */}
      <Alert
        type="info"
        title="Trading Rules"
        content={
          <Row gutter={[16, 8]}>
            <Col xs={24} md={6}>
              <Text style={{ fontSize: 12 }}>
                New Orders: TODAY only ({todayDate.format('YYYY-MM-DD')})
              </Text>
            </Col>
            <Col xs={24} md={6}>
              <Text style={{ fontSize: 12 }}>
                DA Cutoff: 11:00 AM daily
              </Text>
            </Col>
            <Col xs={24} md={6}>
              <Text style={{ fontSize: 12 }}>
                RT Trading: 24/7 available
              </Text>
            </Col>
            <Col xs={24} md={6}>
              <Text style={{ fontSize: 12 }}>
                View History: Use date filter in table
              </Text>
            </Col>
          </Row>
        }
        style={{ marginTop: 20 }}
      />
    </div>
  )
}

export default OrderManagement