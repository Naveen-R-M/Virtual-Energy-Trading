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
  Progress,
  Modal,
  Message,
  Radio,
  Tooltip,
  Badge,
  ConfigProvider,
  DatePicker
} from '@arco-design/web-react'
import {
  IconPlus,
  IconDelete,
  IconRefresh,
  IconClockCircle,
  IconThunderbolt,
  IconCalendar,
  IconQuestion
} from '@arco-design/web-react/icon'
import dayjs from 'dayjs'
import ModernStepper from '../components/ModernStepper'


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
  status: 'pending' | 'filled' | 'rejected'
  fillPrice?: number
  pnl?: number
  createdAt: string
  node: string
  timeSlot?: string // For RT market 5-min slots
}

const OrderManagement: React.FC = () => {
  const [form] = Form.useForm()
  const [selectedMarket, setSelectedMarket] = useState<MarketType>('day-ahead')
  const [orders, setOrders] = useState<Order[]>([
    {
      id: 'ORD-001',
      market: 'day-ahead',
      hour: '09:00',
      side: 'buy',
      quantity: 2.5,
      limitPrice: 48.50,
      status: 'filled',
      fillPrice: 47.25,
      pnl: 312.50,
      createdAt: dayjs().subtract(2, 'hour').format('YYYY-MM-DD HH:mm:ss'),
      node: 'PJM_RTO'
    },
    {
      id: 'ORD-002',
      market: 'day-ahead',
      hour: '10:00', 
      side: 'sell',
      quantity: 1.8,
      limitPrice: 52.25,
      status: 'filled',
      fillPrice: 53.10,
      pnl: 153.00,
      createdAt: dayjs().subtract(1, 'hour').format('YYYY-MM-DD HH:mm:ss'),
      node: 'PJM_RTO'
    },
    {
      id: 'ORD-003',
      market: 'real-time',
      hour: '15:00',
      timeSlot: '15:05',
      side: 'buy',
      quantity: 1.2,
      limitPrice: 55.00,
      status: 'pending',
      createdAt: dayjs().subtract(30, 'minute').format('YYYY-MM-DD HH:mm:ss'),
      node: 'PJM_RTO'
    },
    {
      id: 'ORD-004',
      market: 'day-ahead',
      hour: '16:00',
      side: 'sell',
      quantity: 1.5,
      limitPrice: 45.00,
      status: 'rejected',
      createdAt: dayjs().subtract(10, 'minute').format('YYYY-MM-DD HH:mm:ss'),
      node: 'PJM_RTO'
    },
    {
      id: 'ORD-005',
      market: 'real-time',
      hour: '17:00',
      timeSlot: '17:15',
      side: 'buy',
      quantity: 0.8,
      limitPrice: 49.75,
      status: 'filled',
      fillPrice: 48.90,
      pnl: 68.00,
      createdAt: dayjs().subtract(5, 'minute').format('YYYY-MM-DD HH:mm:ss'),
      node: 'PJM_RTO'
    },
    {
      id: 'ORD-006',
      market: 'day-ahead',
      hour: '18:00',
      side: 'sell',
      quantity: 2.3,
      limitPrice: 52.80,
      status: 'filled',
      fillPrice: 51.20,
      pnl: -368.00,
      createdAt: dayjs().subtract(1, 'minute').format('YYYY-MM-DD HH:mm:ss'),
      node: 'PJM_RTO'
    }
  ])

  const [loading, setLoading] = useState(false)
  const [selectedHour, setSelectedHour] = useState<string>('')
  const [selectedTimeSlot, setSelectedTimeSlot] = useState<string>('')
  const [rtCountdown, setRtCountdown] = useState<string>('')
  const [currentPosition, setCurrentPosition] = useState<any>(null)
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterMarket, setFilterMarket] = useState<string>('all')

  // Generate hour options for Day-Ahead market
  const dayAheadHourOptions = Array.from({ length: 24 }, (_, i) => {
    const hour = dayjs().startOf('day').add(i, 'hour')
    return {
      label: hour.format('HH:mm'),
      value: hour.format('HH:mm'),
      disabled: false
    }
  })

  // Generate upcoming 5-minute time slot options for Real-Time market with countdown
  const generateRealTimeSlots = () => {
    const now = new Date()
    const slots = []
    const currentMinutes = now.getMinutes()
    const nextSlotMinutes = Math.ceil(currentMinutes / 5) * 5
    
    // Generate next 12 slots (1 hour of options)
    for (let i = 0; i < 12; i++) {
      const slotTime = new Date(now)
      slotTime.setMinutes(nextSlotMinutes + i * 5, 0, 0)
      
      // Calculate time difference
      const diffMs = slotTime.getTime() - now.getTime()
      const diffMinutes = Math.floor(diffMs / 60000)
      const diffSeconds = Math.floor((diffMs % 60000) / 1000)
      
      // Format countdown
      const countdown = `${String(diffMinutes).padStart(2, '0')}:${String(diffSeconds).padStart(2, '0')}`
      
      // Check if slot is within locked scheduling window (2 minutes)
      const isLocked = diffMs < 120000 // Less than 2 minutes
      
      slots.push({
        label: dayjs(slotTime).format('HH:mm'),
        value: dayjs(slotTime).format('HH:mm'),
        disabled: isLocked,
        countdown: countdown,
        description: i === 0 ? 'Next slot' : `In ${countdown}`,
        isNextSlot: i === 0,
        diffMs: diffMs
      })
    }
    return slots
  }

  const [realTimeSlots, setRealTimeSlots] = useState(generateRealTimeSlots())
  
  // Update RT slots every second for countdown
  useEffect(() => {
    const timer = setInterval(() => {
      setRealTimeSlots(generateRealTimeSlots())
    }, 1000)
    
    return () => clearInterval(timer)
  }, [])
  
  // Auto-select next available slot when switching to RT market
  useEffect(() => {
    if (selectedMarket === 'real-time') {
      const nextAvailableSlot = realTimeSlots.find(slot => !slot.disabled)
      if (nextAvailableSlot && !selectedTimeSlot) {
        setSelectedTimeSlot(nextAvailableSlot.value)
        form.setFieldValue('timeSlot', nextAvailableSlot.value)
        form.setFieldValue('hour', nextAvailableSlot.value.split(':')[0] + ':00')
      }
    }
  }, [selectedMarket, realTimeSlots])

  // Market rules and constraints
  const getMarketRules = (market: MarketType) => {
    if (market === 'day-ahead') {
      return {
        cutoffTime: '11:00 AM',
        maxOrdersPerSlot: 10,
        timeIncrement: '1 hour',
        description: 'Submit bids before 11AM for hourly delivery slots',
        settlement: 'Settled at DA closing price'
      }
    } else {
      return {
        cutoffTime: 'Continuous',
        maxOrdersPerSlot: 50, // Higher limit for RT
        timeIncrement: '5 minutes',
        description: 'Continuous trading in 5-minute intervals',
        settlement: 'Immediate settlement at RT price'
      }
    }
  }

  // Count orders per time slot based on market type
  const getOrdersPerSlot = (market: MarketType, timeSlot: string) => {
    if (market === 'day-ahead') {
      return orders.filter(order => 
        order.market === 'day-ahead' && order.hour === timeSlot
      ).length
    } else {
      return orders.filter(order => 
        order.market === 'real-time' && order.timeSlot === timeSlot
      ).length
    }
  }

  const currentSlotOrders = selectedMarket === 'day-ahead' ? 
    (selectedHour ? getOrdersPerSlot(selectedMarket, selectedHour) : 0) :
    (selectedTimeSlot ? getOrdersPerSlot(selectedMarket, selectedTimeSlot) : 0)
  const maxOrdersPerSlot = getMarketRules(selectedMarket).maxOrdersPerSlot
  const marketRules = getMarketRules(selectedMarket)

  // Check if market is open based on type
  const isMarketOpen = (market: MarketType) => {
    if (market === 'day-ahead') {
      return dayjs().hour() < 11 // DA market closes at 11 AM
    } else {
      return true // RT market is always open
    }
  }

  // Fetch current position when time slot changes
  useEffect(() => {
    const fetchPosition = async () => {
      if (!selectedHour && !selectedTimeSlot) return
      
      try {
        const timeSlot = selectedMarket === 'real-time' ? selectedTimeSlot : selectedHour
        if (!timeSlot) return
        
        // Mock position data for demo
        const mockPosition = {
          current_net_position: Math.random() * 5,
          projected_net_position: Math.random() * 10,
          buy_volume: Math.random() * 15,
          sell_volume: Math.random() * 5
        }
        
        setCurrentPosition(mockPosition)
      } catch (error) {
        console.error('Error fetching position:', error)
      }
    }
    
    fetchPosition()
  }, [selectedHour, selectedTimeSlot, selectedMarket])

  const handleSubmitOrder = async (values: any) => {
    setLoading(true)
    
    // Validate market-specific rules
    if (selectedMarket === 'day-ahead' && !isMarketOpen('day-ahead')) {
      Message.error('Day-Ahead market is closed. Orders must be submitted before 11:00 AM')
      setLoading(false)
      return
    }

    if (currentSlotOrders >= maxOrdersPerSlot) {
      Message.error(`Maximum ${maxOrdersPerSlot} orders per ${marketRules.timeIncrement} reached`)
      setLoading(false)
      return
    }

    // Client-side position validation
    if (values.side === 'sell' && currentPosition) {
      const maxSellable = Math.max(0, currentPosition.projected_net_position)
      if (values.quantity > maxSellable) {
        Message.error(
          `Cannot sell ${values.quantity} MWh. Maximum sellable: ${maxSellable.toFixed(1)} MWh`
        )
        setLoading(false)
        return
      }
    }

    setTimeout(() => {
      const newOrder: Order = {
        id: `ORD-${String(orders.length + 1).padStart(3, '0')}`,
        market: selectedMarket,
        hour: selectedMarket === 'day-ahead' ? values.hour : values.timeSlot?.split(':')[0] + ':00',
        timeSlot: selectedMarket === 'real-time' ? values.timeSlot : undefined,
        side: values.side,
        quantity: values.quantity,
        limitPrice: values.limitPrice,
        status: 'pending',
        createdAt: dayjs().format('YYYY-MM-DD HH:mm:ss'),
        node: 'PJM_RTO'
      }
      
      setOrders(prev => [newOrder, ...prev])
      form.resetFields()
      setSelectedHour('')
      setSelectedTimeSlot('')
      setLoading(false)
      Message.success(`${selectedMarket === 'day-ahead' ? 'Day-Ahead' : 'Real-Time'} order submitted successfully`)
    }, 800)
  }

  const handleDeleteOrder = (orderId: string) => {
    Modal.confirm({
      title: 'Delete Order',
      content: 'Are you sure you want to delete this order?',
      okButtonProps: { status: 'danger' },
      onOk: () => {
        setOrders(prev => prev.filter(order => order.id !== orderId))
        Message.success('Order deleted')
      }
    })
  }

  // Filter orders by status and market
  const filteredOrders = orders.filter(order => {
    const statusMatch = filterStatus === 'all' || order.status === filterStatus
    const marketMatch = filterMarket === 'all' || order.market === filterMarket
    return statusMatch && marketMatch
  })

  const columns = [
    {
      title: 'Order ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      render: (id: string) => (
        <span style={{ 
          fontFamily: 'monospace', 
          fontWeight: 700, 
          color: '#000000',
          opacity: 1,
          WebkitTextFillColor: '#000000',
          textShadow: 'none'
        }}>
          {id}
        </span>
      )
    },
    {
      title: 'Market',
      dataIndex: 'market',
      key: 'market',
      width: 90,
      render: (market: MarketType) => (
        <Tag className={market === 'day-ahead' ? 'tag-da-market' : 'tag-rt-market'}>
          {market === 'day-ahead' ? 'DA' : 'RT'}
        </Tag>
      )
    },
    {
      title: 'Time',
      dataIndex: 'hour',
      key: 'time',
      width: 80,
      render: (hour: string, record: Order) => (
        <div style={{ fontWeight: 700, color: '#000000' }}>
          <div>{hour}</div>
          {record.market === 'real-time' && record.timeSlot && (
            <div style={{ fontSize: 10, color: '#666666' }}>
              {record.timeSlot}
            </div>
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
      render: (quantity: number) => (
        <Text className="price-display" style={{ color: '#000000' }}>{quantity.toFixed(1)} MWh</Text>
      )
    },
    {
      title: 'Limit Price',
      dataIndex: 'limitPrice',
      key: 'limitPrice',
      width: 100,
      render: (price: number) => (
        <Text className="price-display" style={{ color: '#000000' }}>${price.toFixed(2)}</Text>
      )
    },
    {
      title: 'Fill Price',
      dataIndex: 'fillPrice',
      key: 'fillPrice',
      width: 100,
      render: (price: number) => price ? (
        <Text className="price-display" style={{ color: '#000000' }}>
          ${price.toFixed(2)}
        </Text>
      ) : (
        <span style={{ color: '#000000', fontWeight: 600 }}>-</span>
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
      render: (pnl: number) => pnl ? (
        <Text className={`price-display ${pnl > 0 ? 'table-pnl-positive' : 'table-pnl-negative'}`}>
          {pnl > 0 ? '+' : ''}${pnl.toFixed(2)}
        </Text>
      ) : (
        <span style={{ color: '#000000', fontWeight: 600 }}>-</span>
      )
    },
    {
      title: '',
      key: 'actions',
      width: 60,
      render: (_, record: Order) => (
        record.status === 'pending' && (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '4px',
              cursor: 'pointer'
            }}
            onClick={() => handleDeleteOrder(record.id)}
          >
            <IconDelete 
              style={{ 
                fontSize: 16, 
                color: '#ff4d4f',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#ff7875';
                e.currentTarget.style.transform = 'scale(1.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#ff4d4f';
                e.currentTarget.style.transform = 'scale(1)';
              }}
            />
          </div>
        )
      )
    }
  ]

  const orderSummary = {
    total: orders.length,
    pending: orders.filter(o => o.status === 'pending').length,
    filled: orders.filter(o => o.status === 'filled').length,
    rejected: orders.filter(o => o.status === 'rejected').length,
    totalPnL: orders.reduce((sum, order) => sum + (order.pnl || 0), 0),
    totalVolume: orders.reduce((sum, order) => sum + order.quantity, 0),
    dayAheadOrders: orders.filter(o => o.market === 'day-ahead').length,
    realTimeOrders: orders.filter(o => o.market === 'real-time').length
  }

  const daMarketOpen = isMarketOpen('day-ahead')
  const rtMarketOpen = isMarketOpen('real-time')

  return (
    <div style={{ maxWidth: 1600, margin: '0 auto' }}>
      {/* Enhanced Market Status with Both Markets */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} md={12}>
          <Alert
            type={daMarketOpen ? 'success' : 'warning'}
            title={
              <Space>
                <IconCalendar />
                Day-Ahead Market
                <Badge count={daMarketOpen ? 'OPEN' : 'CLOSED'} 
                       style={{ background: daMarketOpen ? '#00ff00' : '#ff6600' }} />
              </Space>
            }
            content={
              daMarketOpen ? 
                `Orders accepted until 11:00 AM. Current: ${dayjs().format('HH:mm')}` :
                'Market closed. Orders will be queued for tomorrow\'s session'
            }
          />
        </Col>
        <Col xs={24} md={12}>
          <Alert
            type="success"
            title={
              <Space>
                <IconThunderbolt />
                Real-Time Market
                <Badge count="LIVE" style={{ background: '#00ff00' }} />
              </Space>
            }
            content="Continuous trading every 5 minutes. Immediate settlement available"
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Enhanced Order Form with Market Selection */}
        <Col xs={24} lg={8}>
          <Card className="webull-card" title="New Order">
            <Form
              form={form}
              layout="vertical"
              onSubmit={handleSubmitOrder}
              requiredSymbol={false}
            >
              {/* Market Type Selection */}
              <FormItem
                label={
                  <Space>
                    Market Type
                    <Tooltip content="Choose between Day-Ahead (hourly) or Real-Time (5-min) markets" />
                  </Space>
                }
                field="market"
                rules={[{ required: true, message: 'Select market type' }]}
              >
                <RadioGroup
                  value={selectedMarket}
                  onChange={(value) => {
                    setSelectedMarket(value)
                    // Reset form and selections when switching markets
                    form.resetFields()
                    setSelectedHour('')
                    setSelectedTimeSlot('')
                  }}
                  style={{ width: '100%' }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <Radio value="day-ahead">
                      <Space>
                        <IconCalendar style={{ fontSize: 14 }} />
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>Day-Ahead Market</div>
                          <div style={{ fontSize: 11, color: '#666' }}>
                            Hourly bids • {daMarketOpen ? 'Open until 11AM' : 'Closed'}
                          </div>
                        </div>
                      </Space>
                    </Radio>
                    <Radio value="real-time">
                      <Space>
                        <IconThunderbolt style={{ fontSize: 14 }} />
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>Real-Time Market</div>
                          <div style={{ fontSize: 11, color: '#666' }}>
                            5-min intervals • Always open
                          </div>
                        </div>
                      </Space>
                    </Radio>
                  </div>
                </RadioGroup>
              </FormItem>

              {/* Market Rules Info */}
              <div style={{
                padding: 12,
                background: selectedMarket === 'day-ahead' ? 'rgba(0, 123, 255, 0.05)' : 'rgba(255, 107, 53, 0.05)',
                borderRadius: 'var(--radius-md)',
                marginBottom: 16,
                border: `1px solid ${selectedMarket === 'day-ahead' ? '#007bff' : '#ff6b35'}`
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                  {selectedMarket === 'day-ahead' ? 'Day-Ahead Rules' : 'Real-Time Rules'}
                  </div>
                  <div style={{ fontSize: 11, color: '#666', lineHeight: 1.6 }}>
                  • {marketRules.description}<br/>
                  • Max {marketRules.maxOrdersPerSlot} orders per {marketRules.timeIncrement}<br/>
                  • {marketRules.settlement}<br/>
                {selectedMarket === 'real-time' && (
                  <span style={{ color: '#ff6b35' }}>
                    • Orders lock 2 minutes before slot start
                  </span>
                )}
                </div>
              </div>

              {/* Real-Time Market Notice */}
              {selectedMarket === 'real-time' && (
                <Alert
                  type="info"
                  content="Orders execute at the start of your chosen 5-minute slot. Slots lock 2 minutes before execution."
                  style={{ marginBottom: 16 }}
                />
              )}

              {/* Hour Selection for Day-Ahead */}
              {selectedMarket === 'day-ahead' && (
                <FormItem
                  label="Hour Slot"
                  field="hour"
                  rules={[{ required: true, message: 'Select hour' }]}
                >
                  <Select
                    placeholder="Select hour slot"
                    options={dayAheadHourOptions}
                    onChange={setSelectedHour}
                    showSearch
                  />
                </FormItem>
              )}

              {/* 5-Minute Time Slot for Real-Time Market */}
              {selectedMarket === 'real-time' && (
                <FormItem
                  label="Execution Time"
                  field="timeSlot"
                  rules={[{ required: true, message: 'Select execution time' }]}
                >
                  <Select
                    placeholder="Select 5-minute slot"
                    value={selectedTimeSlot || form.getFieldValue('timeSlot')}
                    onChange={(value) => {
                      setSelectedTimeSlot(value)
                      setSelectedHour(value.split(':')[0] + ':00')
                      form.setFieldValue('hour', value.split(':')[0] + ':00')
                    }}
                  >
                    {realTimeSlots.map((slot, idx) => (
                      <Select.Option 
                        key={slot.value} 
                        value={slot.value}
                        disabled={slot.disabled}
                      >
                        <div style={{ 
                          display: 'flex', 
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          width: '100%'
                        }}>
                          <span style={{
                            fontWeight: slot.isNextSlot ? 600 : 400,
                            color: slot.disabled ? '#999' : '#000'
                          }}>
                            {slot.label}
                          </span>
                          <span style={{ 
                            fontSize: 11, 
                            color: slot.disabled ? '#999' : '#666',
                            fontFamily: 'monospace'
                          }}>
                            {slot.isNextSlot ? 
                              (slot.disabled ? 'Locked' : `Next slot - starts in ${slot.countdown}`) : 
                              `In ${slot.countdown}`
                            }
                          </span>
                        </div>
                      </Select.Option>
                    ))}
                  </Select>
                </FormItem>
              )}

              {/* Show countdown timer for selected RT slot */}
              {selectedMarket === 'real-time' && selectedTimeSlot && (
                <div style={{
                  padding: 8,
                  background: 'rgba(255, 107, 53, 0.1)',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: 12,
                  textAlign: 'center',
                  fontSize: 12
                }}>
                  {(() => {
                    const selectedSlot = realTimeSlots.find(s => s.value === selectedTimeSlot)
                    if (!selectedSlot) return null
                    return (
                      <span>
                        <IconClockCircle style={{ marginRight: 4, fontSize: 12 }} />
                        Execution in <span style={{ 
                          fontFamily: 'monospace', 
                          fontWeight: 600,
                          color: selectedSlot.diffMs < 60000 ? '#ff4d4f' : '#ff6b35'
                        }}>
                          {selectedSlot.countdown}
                        </span>
                      </span>
                    )
                  })()}
                </div>
              )}

              {/* Order Limit Progress */}
              {((selectedMarket === 'day-ahead' && selectedHour) || 
                (selectedMarket === 'real-time' && selectedTimeSlot)) && (
                <div style={{
                  padding: 12,
                  background: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: 16,
                  border: '1px solid var(--border-primary)'
                }}>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between',
                    marginBottom: 8,
                    fontSize: 12
                  }}>
                    <Text>
                      {selectedMarket === 'day-ahead' ? 
                        `Orders for ${selectedHour}` : 
                        `RT Orders at ${form.getFieldValue('timeSlot')}`
                      }
                    </Text>
                    <Text style={{ fontFamily: 'monospace' }}>
                      {currentSlotOrders}/{maxOrdersPerSlot}
                    </Text>
                  </div>
                  <Progress
                    percent={(currentSlotOrders / maxOrdersPerSlot) * 100}
                    status={currentSlotOrders >= maxOrdersPerSlot ? 'danger' : 'normal'}
                    showText={false}
                    strokeWidth={4}
                  />
                </div>
              )}

              {/* Show warning if selected slot is about to lock */}
              {selectedMarket === 'real-time' && selectedTimeSlot && (() => {
                const selectedSlot = realTimeSlots.find(s => s.value === selectedTimeSlot)
                if (selectedSlot && selectedSlot.diffMs < 180000 && selectedSlot.diffMs > 120000) {
                  return (
                    <Alert
                      type="warning"
                      content={`Warning: This slot will lock in ${Math.floor((selectedSlot.diffMs - 120000) / 1000)} seconds`}
                      style={{ marginBottom: 12 }}
                    />
                  )
                }
                return null
              })()}

              {/* Position Info for selected slot */}
              {currentPosition && ((selectedMarket === 'day-ahead' && selectedHour) || 
                (selectedMarket === 'real-time' && selectedTimeSlot)) && (
                <div style={{
                  padding: 12,
                  background: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: 16,
                  border: '1px solid var(--border-primary)'
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>
                    Current Position
                  </div>
                  <div style={{ fontSize: 11, lineHeight: 1.6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>Net Position:</span>
                      <span style={{ 
                        fontFamily: 'monospace',
                        fontWeight: 600,
                        color: currentPosition.current_net_position > 0 ? '#00cc00' : 
                               currentPosition.current_net_position < 0 ? '#ff4d4f' : '#666'
                      }}>
                        {currentPosition.current_net_position > 0 ? '+' : ''}
                        {currentPosition.current_net_position.toFixed(1)} MWh
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>Max Sellable:</span>
                      <span style={{ fontFamily: 'monospace', color: '#666' }}>
                        {Math.max(0, currentPosition.projected_net_position).toFixed(1)} MWh
                      </span>
                    </div>
                    {currentPosition.current_net_position === 0 && form.getFieldValue('side') === 'sell' && (
                      <Alert
                        type="warning"
                        content="You must buy energy before you can sell it"
                        style={{ marginTop: 8 }}
                      />
                    )}
                  </div>
                </div>
              )}

              <FormItem
                label="Side"
                field="side"
                rules={[{ required: true, message: 'Select side' }]}
              >
                <Select
                  placeholder="Buy / Sell"
                  options={[
                    { label: 'Buy', value: 'buy' },
                    { label: 'Sell', value: 'sell' }
                  ]}
                />
              </FormItem>

              <Row gutter={16}>
                <Col span={12}>
                  <FormItem
                    label="Quantity (MWh)"
                    field="quantity"
                    rules={[
                      { required: true, message: 'Enter quantity' },
                      { type: 'number', min: 0.1, message: 'Min: 0.1 MWh' },
                      { type: 'number', max: selectedMarket === 'day-ahead' ? 100 : 10, 
                        message: `Max: ${selectedMarket === 'day-ahead' ? 100 : 10} MWh` },
                      {
                        validator: (value, callback) => {
                          if (form.getFieldValue('side') === 'sell' && currentPosition) {
                            const maxSellable = Math.max(0, currentPosition.projected_net_position)
                            if (value > maxSellable) {
                              callback(`Maximum sellable: ${maxSellable.toFixed(1)} MWh`)
                            }
                          }
                          callback()
                        }
                      }
                    ]}
                  >
                    <ModernStepper
                      value={form.getFieldValue('quantity') || 1.0}
                      onChange={(val) => form.setFieldValue('quantity', val)}
                      min={0.1}
                      max={selectedMarket === 'day-ahead' ? 100 : 10}
                      step={0.1}
                      precision={1}
                      placeholder="1.0"
                    />
                  </FormItem>
                </Col>
                
                <Col span={12}>
                  <FormItem
                    label="Limit Price ($/MWh)"
                    field="limitPrice"
                    rules={[
                      { required: true, message: 'Enter price' },
                      { type: 'number', min: 0.01, message: 'Min: $0.01' }
                    ]}
                  >
                    <ModernStepper
                      value={form.getFieldValue('limitPrice') || 1.0}
                      onChange={(val) => form.setFieldValue('limitPrice', val)}
                      min={0.01}
                      max={1000}
                      step={0.01}
                      precision={2}
                      placeholder="1.00"
                    />
                  </FormItem>
                </Col>
              </Row>

              <FormItem>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  long
                  disabled={
                    (selectedMarket === 'day-ahead' && !daMarketOpen) ||
                    currentSlotOrders >= maxOrdersPerSlot
                  }
                >
                  {!isMarketOpen(selectedMarket) ? 
                    'Market Closed' : 
                    currentSlotOrders >= maxOrdersPerSlot ? 
                    'Slot Limit Reached' : 
                    `Submit ${selectedMarket === 'day-ahead' ? 'DA' : 'RT'} Order`
                  }
                </Button>
              </FormItem>
            </Form>
          </Card>

          {/* Enhanced Portfolio Summary with Market Breakdown */}
          <Card className="webull-card" title="Portfolio Summary" style={{ marginTop: 16 }}>
            <Row gutter={[12, 12]}>
              <Col span={8}>
                <div style={{ textAlign: 'center', padding: 12 }}>
                  <div className="webull-kpi-value professional-number neutral">
                    {orderSummary.dayAheadOrders}
                  </div>
                  <div className="webull-kpi-subtitle">DA Orders</div>
                </div>
              </Col>
              <Col span={8}>
                <div style={{ textAlign: 'center', padding: 12 }}>
                  <div className="webull-kpi-value professional-number neutral">
                    {orderSummary.realTimeOrders}
                  </div>
                  <div className="webull-kpi-subtitle">RT Orders</div>
                </div>
              </Col>
              <Col span={8}>
                <div style={{ textAlign: 'center', padding: 12 }}>
                  <div className="webull-kpi-value professional-number neutral">
                    {orderSummary.totalVolume.toFixed(1)}
                  </div>
                  <div className="webull-kpi-subtitle">Total MWh</div>
                </div>
              </Col>
            </Row>
            
            <div style={{ 
              textAlign: 'center',
              padding: 20,
              marginTop: 16,
              borderTop: '1px solid var(--border-primary)'
            }}>
              <div className={`webull-kpi-value professional-number ${
                orderSummary.totalPnL >= 0 ? 'positive' : 'negative'
              }`}>
                {orderSummary.totalPnL >= 0 ? '+' : ''}${orderSummary.totalPnL.toFixed(2)}
              </div>
              <div className="webull-kpi-subtitle">Portfolio P&L</div>
              <div style={{ marginTop: 8, fontSize: 11 }}>
                <Text style={{ color: orderSummary.totalPnL >= 0 ? '#006600' : '#cc0000' }}>
                  {orderSummary.totalPnL >= 0 ? '▲ Profitable' : '▼ Loss Position'}
                </Text>
              </div>
            </div>
          </Card>
        </Col>

        {/* Enhanced Orders Table with Market Filter */}
        <Col xs={24} lg={16}>
          <Card 
            className="webull-card"
            title="Order Management"
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
                    { label: 'All', value: 'all' },
                    { label: 'Pending', value: 'pending' },
                    { label: 'Filled', value: 'filled' },
                    { label: 'Rejected', value: 'rejected' }
                  ]}
                />
                <Button 
                  icon={<IconRefresh />}
                  size="small"
                >
                  Refresh
                </Button>
              </Space>
            }
          >
            <Table
              columns={columns}
              data={filteredOrders}
              pagination={{
                pageSize: 10,
                size: 'small',
                showTotal: true,
                showJumper: false,
                showPageSize: false
              }}
              scroll={{ x: 900 }}
              rowKey="id"
              loading={loading}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* Enhanced Trading Rules with Market-Specific Information */}
      <Card 
        className="webull-card"
        title="Market Rules & Information"
        style={{ marginTop: 20 }}
      >
        <Row gutter={[24, 16]}>
          {/* Day-Ahead Market Rules */}
          <Col xs={24} lg={12}>
            <div style={{
              padding: 16,
              background: 'rgba(0, 123, 255, 0.05)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid #007bff'
            }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center',
                marginBottom: 12
              }}>
                <IconCalendar style={{ fontSize: 16, marginRight: 8, color: '#007bff' }} />
                <div style={{ fontWeight: 600, fontSize: 14 }}>Day-Ahead Market</div>
              </div>
              
              <div style={{ fontSize: 12, lineHeight: 1.5 }}>
                <div style={{ marginBottom: 8 }}>
                  <strong>Timing:</strong> Submit before 11:00 AM daily
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Increments:</strong> 1-hour delivery slots
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Limits:</strong> Up to 10 orders per hour slot
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Settlement:</strong> All qualifying bids settled at DA closing price
                </div>
                <div>
                  <strong>P&L:</strong> Offset against real-time prices during delivery hour
                </div>
              </div>
            </div>
          </Col>

          {/* Real-Time Market Rules */}
          <Col xs={24} lg={12}>
            <div style={{
              padding: 16,
              background: 'rgba(255, 107, 53, 0.05)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid #ff6b35'
            }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center',
                marginBottom: 12
              }}>
                <IconThunderbolt style={{ fontSize: 16, marginRight: 8, color: '#ff6b35' }} />
                <div style={{ fontWeight: 600, fontSize: 14 }}>Real-Time Market</div>
              </div>
              
              <div style={{ fontSize: 12, lineHeight: 1.5 }}>
                <div style={{ marginBottom: 8 }}>
                  <strong>Timing:</strong> Continuous trading (24/7)
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Increments:</strong> 5-minute slots (immediate execution)
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Limits:</strong> Up to 50 orders per 5-min slot
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Settlement:</strong> Immediate settlement at current RT price
                </div>
                <div>
                  <strong>P&L:</strong> Immediate realization at settlement
                </div>
              </div>
            </div>
          </Col>
        </Row>

        {/* Trading Strategy Tips */}
        <div style={{
          marginTop: 20,
          padding: 16,
          background: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-primary)'
        }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
            💡 Trading Strategy
          </div>
          <div style={{ fontSize: 11, color: '#666', lineHeight: 1.5 }}>
            <strong>Day-Ahead:</strong> Use for planned positions. Buy low during off-peak hours, sell high during peak demand periods.<br/>
            <strong>Real-Time:</strong> Use for quick arbitrage opportunities. React to immediate price movements and imbalances.
          </div>
        </div>
      </Card>
    </div>
  )
}

export default OrderManagement