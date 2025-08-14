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
  Spin
} from '@arco-design/web-react'
import {
  IconUp,
  IconDown,
  IconRefresh
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
  Cell,
  AreaChart,
  Area
} from 'recharts'
import dayjs from 'dayjs'
import HotReloadTest from '../components/HotReloadTest'
import EnhancedPriceChart from '../components/EnhancedPriceChart'

const { Row, Col } = Grid
const { Title, Text } = Typography

// Enhanced mock data generator with more realistic P&L variations
const generateMockPnLData = () => {
  let cumulative = 0
  return Array.from({ length: 7 }, (_, i) => {
    // Create more realistic P&L pattern with some losses
    const patterns = [1200, 850, -420, 1680, -320, 950, -150]
    const dailyPnL = patterns[i] + (Math.random() - 0.5) * 200
    cumulative += dailyPnL
    const day = dayjs().subtract(6 - i, 'day')
    return {
      day: day.format('MMM DD'),
      dailyPnL: Math.round(dailyPnL),
      cumulativePnL: Math.round(cumulative),
      color: dailyPnL >= 0 ? '#4caf50' : '#f44336'
    }
  })
}

const generateMockPriceData = () => {
  const data = []
  const now = dayjs()
  
  for (let i = 0; i < 24; i++) {
    const hour = now.startOf('day').add(i, 'hour')
    
    let basePrice = 45
    
    if (i >= 6 && i <= 9) {
      basePrice = 42 + (i - 6) * 8
    } else if (i >= 14 && i <= 18) {
      basePrice = 68 + Math.sin((i - 14) / 2) * 12
    } else if (i >= 19 && i <= 23) {
      basePrice = 52 - (i - 19) * 4
    } else {
      basePrice = 32 + Math.random() * 8
    }
    
    const daPrice = Math.max(15, basePrice + (Math.random() - 0.5) * 6)
    const rtPrice = Math.max(12, daPrice + (Math.random() - 0.5) * 12)
    
    data.push({
      hour: hour.format('HH:mm'),
      daPrice: Math.round(daPrice * 100) / 100,
      rtPrice: Math.round(rtPrice * 100) / 100,
      spread: Math.round((rtPrice - daPrice) * 100) / 100
    })
  }
  return data
}

const mockOrderData = [
  {
    id: 'ORD-001',
    time: '09:30',
    hour: '14:00',
    side: 'Buy',
    quantity: 2.5,
    price: 48.50,
    fillPrice: 47.25,
    status: 'Filled',
    pnl: 312.50
  },
  {
    id: 'ORD-002',
    time: '10:15', 
    hour: '15:00',
    side: 'Sell',
    quantity: 1.8,
    price: 52.25,
    fillPrice: 53.10,
    status: 'Filled',
    pnl: 153.00
  },
  {
    id: 'ORD-003',
    time: '11:45',
    hour: '16:00',
    side: 'Buy',
    quantity: 4.2,
    price: 55.00,
    status: 'Pending',
    pnl: 0
  },
  {
    id: 'ORD-004',
    time: '12:20',
    hour: '17:00', 
    side: 'Sell',
    quantity: 2.1,
    price: 51.00,
    fillPrice: 49.80,
    status: 'Filled',
    pnl: -252.00 // Loss example in red
  },
  {
    id: 'ORD-005',
    time: '13:10',
    hour: '18:00',
    side: 'Buy', 
    quantity: 1.5,
    price: 46.75,
    fillPrice: 48.20,
    status: 'Filled',
    pnl: -217.50 // Another loss example
  }
]

const Dashboard: React.FC = () => {
  const [priceData, setPriceData] = useState(generateMockPriceData())
  const [pnlData, setPnlData] = useState(generateMockPnLData())
  const [selectedDate, setSelectedDate] = useState(dayjs())
  const [selectedNode, setSelectedNode] = useState('PJM_RTO')
  const [loading, setLoading] = useState(false)

  const refreshData = () => {
    setLoading(true)
    setTimeout(() => {
      setPriceData(generateMockPriceData())
      setPnlData(generateMockPnLData())
      setLoading(false)
    }, 1200)
  }

  // Calculate KPIs
  const totalPnL = pnlData[pnlData.length - 1]?.cumulativePnL || 0
  const todayPnL = pnlData[pnlData.length - 1]?.dailyPnL || 0
  const filledOrders = mockOrderData.filter(o => o.status === 'Filled').length
  const totalOrders = mockOrderData.length
  const profitableOrders = mockOrderData.filter(o => o.pnl > 0).length
  const winRate = Math.round((profitableOrders / filledOrders) * 100) || 0

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
      title: 'Time',
      dataIndex: 'hour',
      key: 'hour',
      width: 80,
      render: (hour: string) => (
        <span style={{ 
          fontWeight: 700, 
          color: '#000000',
          opacity: 1,
          WebkitTextFillColor: '#000000',
          textShadow: 'none'
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
        <Text className="price-display" style={{ color: '#000000' }}>{qty.toFixed(1)} MWh</Text>
      )
    },
    {
      title: 'Price',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      render: (price: number) => (
        <Text className="price-display" style={{ color: '#000000' }}>${price.toFixed(2)}</Text>
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
      const value = payload[0]?.value
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
              {entry.name}: ${entry.value.toFixed(2)}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  const PnLTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const value = payload[0].value
      return (
        <div className="custom-tooltip">
          <p style={{ margin: 0, fontWeight: 600, fontSize: 12, color: '#d1d4dc' }}>
            {label}
          </p>
          <p style={{ 
            margin: '4px 0', 
            color: value >= 0 ? '#006600' : '#cc0000',
            fontWeight: 600,
            fontSize: 11
          }}>
            Daily P&L: {value >= 0 ? '+' : ''}${value.toFixed(2)}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div style={{ maxWidth: 1600, margin: '0 auto' }}>
      {/* Clean Controls */}
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
                  value={selectedDate}
                  onChange={setSelectedDate}
                  size="small"
                />
              </Space>
              <Button 
                type="primary" 
                icon={<IconRefresh />}
                onClick={refreshData}
                loading={loading}
                size="small"
              >
                Refresh
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Professional KPI Cards with Red/Green P&L */}
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
              {totalPnL >= 0 ? 'Profitable Portfolio' : 'Loss Position'}
            </div>
          </div>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <div className="webull-kpi-card">
            <div className="webull-kpi-title">Today's P&L</div>
            <div className={`webull-kpi-value professional-number ${todayPnL >= 0 ? 'positive' : 'negative'}`}>
              ${todayPnL >= 0 ? '+' : ''}${todayPnL.toFixed(2)}
            </div>
            <div className="webull-kpi-subtitle">
              Updated: {dayjs().format('HH:mm')}
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

      {/* Professional Charts */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {/* Price Chart */}
        <Col xs={24} lg={16}>
          <Card 
            className="webull-card"
            title="Market Prices - Day-Ahead vs Real-Time"
            extra={
              <Tag style={{ background: '#ffffff', color: '#000000', fontSize: 10, fontWeight: 600 }}>
                LIVE
              </Tag>
            }
            style={{ height: 450 }}
          >
            {loading ? (
              <div className="loading-spinner">
                <Spin size={32} />
                <Text style={{ marginTop: 12, fontSize: 12 }}>
                  Loading market data...
                </Text>
              </div>
            ) : (
              <EnhancedPriceChart loading={loading} />
            )}
          </Card>
        </Col>

        {/* Performance Donut - Green/Red Theme */}
        <Col xs={24} lg={8}>
          <Card 
            className="webull-card"
            title="Trading Performance"
            style={{ height: 400 }}
          >
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
          </Card>
        </Col>
      </Row>

      {/* FIXED: P&L Chart with Red/Green Bars */}
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
                <Tooltip content={<PnLTooltip />} />
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
            
            {/* Chart Summary */}
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
          </Card>
        </Col>
      </Row>

      {/* Recent Orders Table with Red/Green P&L */}
      <Row>
        <Col span={24}>
          <Card 
            className="webull-card"
            title="Recent Orders"
            extra={
              <Space>
                <Text type="secondary" style={{ fontSize: 10 }}>
                  {mockOrderData.length} ORDERS
                </Text>
                <Button 
                  type="primary" 
                  size="small"
                  onClick={() => window.location.hash = '/orders'}
                >
                  View All
                </Button>
              </Space>
            }
          >
            <Table
              columns={orderColumns}
              data={mockOrderData}
              pagination={false}
              scroll={{ x: 700 }}
              rowKey="id"
              size="small"
              showHeader={true}
            />
          </Card>
        </Col>
      </Row>

      {/* Market Rules */}
      <Alert
        type="info"
        title="Market Information"
        content={
          <Row gutter={[16, 8]}>
            <Col xs={24} md={8}>
              <Text style={{ fontSize: 12 }}>
                Cutoff: 11:00 AM daily
              </Text>
            </Col>
            <Col xs={24} md={8}>
              <Text style={{ fontSize: 12 }}>
                Max: 10 orders/hour
              </Text>
            </Col>
            <Col xs={24} md={8}>
              <Text style={{ fontSize: 12 }}>
                Settlement: DA closing price
              </Text>
            </Col>
          </Row>
        }
        style={{ marginTop: 20 }}
      />

      {/* Hot Reload Test - Hidden in production */}
      {process.env.NODE_ENV === 'development' && <HotReloadTest />}
    </div>
  )
}

export default Dashboard
