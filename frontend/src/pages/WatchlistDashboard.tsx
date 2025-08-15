import React, { useState, useEffect } from 'react'
import {
  Card,
  Space,
  Typography,
  Button,
  Input,
  Modal,
  Select,
  Tag,
  Badge,
  Alert,
  Tooltip,
  Spin,
  Message
} from '@arco-design/web-react'
import {
  IconPlus,
  IconSearch,
  IconStar,
  IconStarFill,
  IconUp,
  IconDown,
  IconRefresh,
  IconNotification,
  IconDelete,
  IconEye
} from '@arco-design/web-react/icon'
import { LineChart, Line, ResponsiveContainer } from 'recharts'

const { Title, Text } = Typography

// Mock data structure
const mockWatchlistData = [
  {
    node_id: 1,
    ticker_symbol: "PJMRTO",
    node_name: "PJM RTO Hub",
    custom_name: null,
    current_price: 42.75,
    price_change_5min: 1.25,
    price_change_percent: 3.01,
    day_ahead_price: 41.50,
    sparkline_data: [40.2, 40.8, 41.1, 41.5, 42.0, 42.3, 42.75],
    last_updated: new Date().toISOString(),
    is_favorite: true
  },
  {
    node_id: 2,
    ticker_symbol: "WESTUB",
    node_name: "Western Hub",
    custom_name: "West Hub",
    current_price: 38.90,
    price_change_5min: -0.85,
    price_change_percent: -2.14,
    day_ahead_price: 39.20,
    sparkline_data: [40.1, 39.8, 39.5, 39.2, 39.0, 38.95, 38.90],
    last_updated: new Date().toISOString(),
    is_favorite: false
  },
  {
    node_id: 3,
    ticker_symbol: "KNY138T61",
    node_name: "Kearneys 138 KV T61",
    custom_name: "Kearneys Transformer",
    current_price: 45.60,
    price_change_5min: 2.10,
    price_change_percent: 4.83,
    day_ahead_price: 44.25,
    sparkline_data: [43.0, 43.8, 44.1, 44.5, 45.0, 45.3, 45.60],
    last_updated: new Date().toISOString(),
    is_favorite: false
  }
]

const mockAvailableNodes = [
  { id: 4, ticker_symbol: "EASTHUB", node_name: "Eastern Hub", zone: "EAST" },
  { id: 5, ticker_symbol: "BALT500", node_name: "Baltimore 500kV", zone: "BGE" },
  { id: 6, ticker_symbol: "NYZCGEN", node_name: "NYC Zone Generator", zone: "NYISO" }
]

// Individual node ticker component
const NodeTicker = ({ node, onToggleFavorite, onRemove, onViewChart }) => {
  const isPositive = node.price_change_5min >= 0
  const spread = node.current_price - (node.day_ahead_price || 0)
  
  // Format sparkline data for chart
  const sparklineData = node.sparkline_data.map((price, index) => ({ 
    value: price, 
    index 
  }))

  return (
    <div 
      style={{
        padding: '16px',
        border: '1px solid #444',
        borderRadius: '8px',
        background: 'rgba(255, 255, 255, 0.03)',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        marginBottom: '8px'
      }}
      onClick={() => onViewChart(node)}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#0066ff'
        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
        e.currentTarget.style.transform = 'translateY(-1px)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#444'
        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'
        e.currentTarget.style.transform = 'translateY(0)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        {/* Left side - Ticker and name */}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Text style={{ 
              fontWeight: 700, 
              fontSize: 16,
              fontFamily: 'monospace',
              color: '#ffffff'
            }}>
              {node.ticker_symbol}
            </Text>
            <Button
              type="text"
              size="mini"
              icon={node.is_favorite ? 
                <IconStarFill style={{ color: '#FFD700' }} /> : 
                <IconStar style={{ color: '#cccccc' }} />
              }
              onClick={(e) => {
                e.stopPropagation()
                onToggleFavorite(node.node_id)
              }}
              style={{ 
                color: '#cccccc',
                background: 'transparent',
                border: 'none'
              }}
            />
            <Button
              type="text"
              size="mini"
              icon={<IconDelete style={{ color: '#ff6666' }} />}
              onClick={(e) => {
                e.stopPropagation()
                onRemove(node.node_id)
              }}
              style={{ 
                color: '#ff6666',
                background: 'transparent',
                border: 'none'
              }}
            />
          </div>
          
          <Text style={{ fontSize: 12, display: 'block', marginTop: 2, color: '#cccccc' }}>
            {node.custom_name || node.node_name}
          </Text>
          
          {/* DA vs RT spread indicator */}
          {node.day_ahead_price && (
            <div style={{ marginTop: 4 }}>
              <Text style={{ 
                fontSize: 10, 
                color: Math.abs(spread) > 2 ? '#ffaa44' : '#cccccc',
                fontWeight: Math.abs(spread) > 2 ? 600 : 400
              }}>
                DA: ${node.day_ahead_price.toFixed(2)} 
                <span style={{ margin: '0 4px' }}>•</span>
                Spread: {spread > 0 ? '+' : ''}${spread.toFixed(2)}
              </Text>
            </div>
          )}
        </div>

        {/* Center - Simple Sparkline chart (no tooltip to avoid overlap) */}
        <div 
          style={{ 
            width: 80, 
            height: 40, 
            margin: '0 16px', 
            position: 'relative',
            pointerEvents: 'none'  // Prevent mouse events on chart
          }}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparklineData}>
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke={isPositive ? '#00cc00' : '#ff4d4f'} 
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              {/* No tooltip to prevent overlap issues */}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Right side - Price and change */}
        <div style={{ textAlign: 'right', minWidth: 100 }}>
          <div style={{
            fontSize: 18,
            fontWeight: 700,
            fontFamily: 'monospace',
            color: '#ffffff'
          }}>
            ${node.current_price.toFixed(2)}
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginTop: 4 }}>
            {isPositive ? 
              <IconUp style={{ fontSize: 12, color: '#00cc00' }} /> : 
              <IconDown style={{ fontSize: 12, color: '#ff4d4f' }} />
            }
            <Text style={{
              fontSize: 12,
              fontWeight: 600,
              color: isPositive ? '#00cc00' : '#ff4d4f',
              marginLeft: 4
            }}>
              {isPositive ? '+' : ''}${node.price_change_5min?.toFixed(2)} ({node.price_change_percent?.toFixed(1)}%)
            </Text>
          </div>
          
          <Text style={{ fontSize: 10, marginTop: 2, color: '#cccccc' }}>
            {new Date(node.last_updated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Text>
        </div>
      </div>
    </div>
  )
}

// Enhanced Chart Modal for full chart view
const ChartModal = ({ visible, onClose, node }) => {
  // Generate more detailed chart data
  const generateDetailedData = () => {
    const hours = 24
    const now = new Date()
    const data = []
    
    for (let i = hours; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 60 * 60 * 1000)
      const basePrice = node?.current_price || 45
      const volatility = (Math.random() - 0.5) * 10
      const price = Math.max(15, basePrice + volatility)
      
      data.push({
        time: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        price: Number(price.toFixed(2)),
        da_price: Number((price + (Math.random() - 0.5) * 5).toFixed(2))
      })
    }
    return data
  }

  const [chartData] = useState(generateDetailedData())

  if (!node) return null

  return (
    <Modal
      title={`${node.ticker_symbol} - Detailed Price Chart`}
      visible={visible}
      onCancel={onClose}
      footer={null}
      width={800}
      style={{ top: 50 }}
    >
      <div style={{ height: 400, background: '#1a1a1a', borderRadius: 8, padding: 16 }}>
        <div style={{ marginBottom: 16 }}>
          <Title level={4} style={{ color: '#ffffff', margin: 0 }}>
            {node.node_name}
          </Title>
          <Text style={{ color: '#cccccc', fontSize: 12 }}>
            Last 24 hours • Real-Time vs Day-Ahead
          </Text>
        </div>
        
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <Line 
              type="monotone" 
              dataKey="price" 
              stroke="#00cc00" 
              strokeWidth={2}
              name="Real-Time"
              dot={false}
            />
            <Line 
              type="monotone" 
              dataKey="da_price" 
              stroke="#0066ff" 
              strokeWidth={2}
              strokeDasharray="5 5"
              name="Day-Ahead"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
        
        <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ width: 12, height: 2, background: '#00cc00', marginRight: 8 }}></div>
            <Text style={{ color: '#cccccc', fontSize: 12 }}>Real-Time</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ width: 12, height: 2, background: '#0066ff', marginRight: 8 }}></div>
            <Text style={{ color: '#cccccc', fontSize: 12 }}>Day-Ahead</Text>
          </div>
        </div>
      </div>
    </Modal>
  )
}

// Add to watchlist modal
const AddToWatchlistModal = ({ visible, onClose, onAdd, availableNodes, loading }) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedNode, setSelectedNode] = useState(null)
  const [customName, setCustomName] = useState('')
  const [isFavorite, setIsFavorite] = useState(false)

  const filteredNodes = availableNodes.filter(node => 
    node.node_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    node.ticker_symbol.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleAdd = () => {
    if (!selectedNode) return
    
    onAdd({
      node_id: selectedNode.id,
      custom_name: customName || null,
      is_favorite: isFavorite
    })
    
    // Reset form
    setSelectedNode(null)
    setCustomName('')
    setIsFavorite(false)
    setSearchTerm('')
  }

  return (
    <Modal
      title="Add to Watchlist"
      visible={visible}
      onOk={handleAdd}
      onCancel={onClose}
      okText="Add to Watchlist"
      okButtonProps={{ disabled: !selectedNode, loading }}
      style={{ background: '#1a1a1a' }}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Search nodes */}
        <div>
          <Text style={{ display: 'block', marginBottom: 8, fontWeight: 600, color: '#ffffff' }}>
            Search PJM Nodes
          </Text>
          <Input
            placeholder="Search by name or ticker..."
            prefix={<IconSearch style={{ color: '#cccccc' }} />}
            value={searchTerm}
            onChange={setSearchTerm}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              borderColor: '#555',
              color: '#ffffff'
            }}
          />
        </div>

        {/* Node selection */}
        <div>
          <Text style={{ display: 'block', marginBottom: 8, fontWeight: 600, color: '#ffffff' }}>
            Select Node
          </Text>
          <div style={{ 
            maxHeight: 200, 
            overflowY: 'auto', 
            border: '1px solid #444', 
            borderRadius: 4,
            background: 'rgba(255, 255, 255, 0.02)'
          }}>
            {filteredNodes.map(node => (
              <div
                key={node.id}
                style={{
                  padding: '12px',
                  cursor: 'pointer',
                  borderBottom: '1px solid #333',
                  background: selectedNode?.id === node.id ? 'rgba(0, 102, 255, 0.2)' : 'transparent',
                  color: '#ffffff'
                }}
                onClick={() => setSelectedNode(node)}
                onMouseEnter={(e) => {
                  if (selectedNode?.id !== node.id) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (selectedNode?.id !== node.id) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 14, color: '#ffffff' }}>
                  {node.ticker_symbol}
                </div>
                <div style={{ fontSize: 12, color: '#cccccc', marginTop: 2 }}>
                  {node.node_name}
                  {node.zone && <Tag size="small" style={{ marginLeft: 8, background: '#333', color: '#cccccc' }}>{node.zone}</Tag>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Customization options */}
        {selectedNode && (
          <div>
            <Text style={{ display: 'block', marginBottom: 8, fontWeight: 600, color: '#ffffff' }}>
              Customize
            </Text>
            <Space direction="vertical" size="medium" style={{ width: '100%' }}>
              <Input
                placeholder="Custom display name (optional)"
                value={customName}
                onChange={setCustomName}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  borderColor: '#555',
                  color: '#ffffff'
                }}
              />
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', color: '#ffffff' }}>
                <input
                  type="checkbox"
                  checked={isFavorite}
                  onChange={(e) => setIsFavorite(e.target.checked)}
                  style={{ marginRight: 8 }}
                />
                <IconStar style={{ marginRight: 4, fontSize: 14, color: '#cccccc' }} />
                Mark as favorite
              </label>
            </Space>
          </div>
        )}
      </Space>
    </Modal>
  )
}

// Main Watchlist Dashboard component
const WatchlistDashboard = () => {
  const [watchlist, setWatchlist] = useState(mockWatchlistData)
  const [loading, setLoading] = useState(false)
  const [addModalVisible, setAddModalVisible] = useState(false)
  const [chartModalVisible, setChartModalVisible] = useState(false)
  const [selectedNode, setSelectedNode] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(new Date())
  const [autoUpdate, setAutoUpdate] = useState(true)

  // Auto-refresh every 5 minutes
  useEffect(() => {
    if (!autoUpdate) return

    const interval = setInterval(() => {
      handleRefresh()
    }, 5 * 60 * 1000) // 5 minutes

    return () => clearInterval(interval)
  }, [autoUpdate])

  const handleRefresh = async () => {
    setLoading(true)
    try {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Update mock data with small price changes
      setWatchlist(prev => prev.map(node => {
        const priceChange = (Math.random() - 0.5) * 2
        const newPrice = Math.max(15, node.current_price + priceChange)
        return {
          ...node,
          current_price: Number(newPrice.toFixed(2)),
          price_change_5min: Number(priceChange.toFixed(2)),
          price_change_percent: Number(((priceChange / node.current_price) * 100).toFixed(2)),
          last_updated: new Date().toISOString()
        }
      }))
      
      setLastUpdate(new Date())
      Message.success('Watchlist updated successfully')
    } catch (error) {
      Message.error('Failed to update watchlist')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleFavorite = async (nodeId) => {
    setWatchlist(prev => prev.map(node => 
      node.node_id === nodeId 
        ? { ...node, is_favorite: !node.is_favorite }
        : node
    ))
    Message.success('Favorite updated')
  }

  const handleRemoveFromWatchlist = async (nodeId) => {
    Modal.confirm({
      title: 'Remove from Watchlist',
      content: 'Are you sure you want to remove this node from your watchlist?',
      okButtonProps: { status: 'danger' },
      onOk: () => {
        setWatchlist(prev => prev.filter(node => node.node_id !== nodeId))
        Message.success('Node removed from watchlist')
      }
    })
  }

  const handleAddToWatchlist = async (request) => {
    try {
      // Simulate adding node
      const newNode = mockAvailableNodes.find(n => n.id === request.node_id)
      if (newNode) {
        const watchlistNode = {
          node_id: newNode.id,
          ticker_symbol: newNode.ticker_symbol,
          node_name: newNode.node_name,
          custom_name: request.custom_name,
          current_price: Number((40 + Math.random() * 20).toFixed(2)),
          price_change_5min: Number(((Math.random() - 0.5) * 3).toFixed(2)),
          price_change_percent: Number(((Math.random() - 0.5) * 5).toFixed(2)),
          day_ahead_price: Number((40 + Math.random() * 20).toFixed(2)),
          sparkline_data: Array.from({ length: 7 }, () => Number((35 + Math.random() * 15).toFixed(2))),
          last_updated: new Date().toISOString(),
          is_favorite: request.is_favorite
        }
        
        setWatchlist(prev => [...prev, watchlistNode])
        Message.success(`${newNode.ticker_symbol} added to watchlist`)
      }
      
      setAddModalVisible(false)
    } catch (error) {
      Message.error('Failed to add to watchlist')
    }
  }

  const handleViewChart = (node) => {
    setSelectedNode(node)
    setChartModalVisible(true)
  }

  const sortedWatchlist = [...watchlist].sort((a, b) => {
    if (a.is_favorite && !b.is_favorite) return -1
    if (!a.is_favorite && b.is_favorite) return 1
    return a.ticker_symbol.localeCompare(b.ticker_symbol)
  })

  const totalValue = watchlist.reduce((sum, node) => sum + node.current_price, 0)
  const totalChange = watchlist.reduce((sum, node) => sum + (node.price_change_5min || 0), 0)
  const positiveNodes = watchlist.filter(node => (node.price_change_5min || 0) >= 0).length

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 16px' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <Title level={2} style={{ margin: 0, fontSize: 24, color: '#ffffff' }}>
              ⚡ PJM Watchlist
            </Title>
            <Text style={{ fontSize: 14, color: '#cccccc' }}>
              Real-time electricity prices • Last update: {lastUpdate.toLocaleTimeString()}
            </Text>
          </div>
          
          <Space>
            <Tooltip content={autoUpdate ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}>
              <Button
                size="small"
                onClick={() => setAutoUpdate(!autoUpdate)}
                style={{
                  background: autoUpdate ? '#0066ff' : 'rgba(255, 255, 255, 0.1)',
                  borderColor: autoUpdate ? '#0066ff' : '#555',
                  color: '#ffffff',
                  fontWeight: 600
                }}
              >
                {autoUpdate ? '🔄 AUTO' : '⏸️ MANUAL'}
              </Button>
            </Tooltip>
            
            <Button
              icon={<IconRefresh style={{ color: '#ffffff' }} />}
              onClick={handleRefresh}
              loading={loading}
              style={{
                borderColor: '#555',
                color: '#ffffff',
                background: 'rgba(255, 255, 255, 0.05)',
                fontWeight: 600
              }}
            >
              Refresh
            </Button>
            
            <Button
              type="primary"
              icon={<IconPlus style={{ color: '#ffffff' }} />}
              onClick={() => setAddModalVisible(true)}
              style={{
                background: '#0066ff',
                borderColor: '#0066ff',
                color: '#ffffff',
                fontWeight: 600
              }}
            >
              Add Node
            </Button>
          </Space>
        </div>

        {/* Summary stats */}
        <div style={{ display: 'flex', gap: 24, marginBottom: 20 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#ffffff' }}>
              {watchlist.length}
            </div>
            <Text style={{ fontSize: 12, color: '#cccccc' }}>Nodes Tracked</Text>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <div style={{ 
              fontSize: 20, 
              fontWeight: 700, 
              color: totalChange >= 0 ? '#00cc00' : '#ff4d4f' 
            }}>
              {totalChange >= 0 ? '+' : ''}${totalChange.toFixed(2)}
            </div>
            <Text style={{ fontSize: 12, color: '#cccccc' }}>Total Change (5m)</Text>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#ffffff' }}>
              ${totalValue.toFixed(2)}
            </div>
            <Text style={{ fontSize: 12, color: '#cccccc' }}>Combined Value</Text>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#00cc00' }}>
              {positiveNodes}/{watchlist.length}
            </div>
            <Text style={{ fontSize: 12, color: '#cccccc' }}>Positive Nodes</Text>
          </div>
        </div>
      </div>

      {/* Market status alert */}
      <Alert
        type="success"
        content="PJM real-time market is operational. Prices updated every 5 minutes."
        style={{ 
          marginBottom: 20,
          background: 'rgba(0, 255, 0, 0.1)',
          borderColor: '#00cc00',
          color: '#ffffff'
        }}
        showIcon
      />

      {/* Watchlist */}
      <Card style={{ 
        padding: 0,
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid #333'
      }}>
        {loading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size={32} />
            <div style={{ marginTop: 12, fontSize: 14, color: '#cccccc' }}>
              Updating prices...
            </div>
          </div>
        )}
        
        {!loading && watchlist.length === 0 && (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📈</div>
            <Title level={4} style={{ color: '#ffffff' }}>No Nodes in Watchlist</Title>
            <Text style={{ display: 'block', marginBottom: 20, color: '#cccccc' }}>
              Add PJM nodes to track real-time electricity prices
            </Text>
            <Button
              type="primary"
              icon={<IconPlus />}
              onClick={() => setAddModalVisible(true)}
              style={{
                background: '#0066ff',
                borderColor: '#0066ff',
                color: '#ffffff'
              }}
            >
              Add Your First Node
            </Button>
          </div>
        )}
        
        {!loading && watchlist.length > 0 && (
          <div style={{ padding: '8px' }}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              {sortedWatchlist.map(node => (
                <NodeTicker
                  key={node.node_id}
                  node={node}
                  onToggleFavorite={handleToggleFavorite}
                  onRemove={handleRemoveFromWatchlist}
                  onViewChart={handleViewChart}
                />
              ))}
            </Space>
          </div>
        )}
      </Card>

      {/* Quick actions */}
      {watchlist.length > 0 && (
        <div style={{ 
          position: 'fixed',
          bottom: 24,
          right: 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 12
        }}>
          <Tooltip content="View detailed charts">
            <Button
              type="primary"
              shape="circle"
              size="large"
              icon={<IconEye style={{ color: '#ffffff' }} />}
              onClick={() => {
                if (watchlist.length === 1) {
                  handleViewChart(watchlist[0])
                } else {
                  Message.info('Click on a node ticker to view detailed chart')
                }
              }}
              style={{
                width: 56,
                height: 56,
                background: '#0066ff',
                borderColor: '#0066ff',
                boxShadow: '0 4px 12px rgba(0, 102, 255, 0.3)'
              }}
            />
          </Tooltip>
        </div>
      )}

      {/* Enhanced Chart Modal for full chart view */}
      <Modal
        title={selectedNode ? `${selectedNode.ticker_symbol} - Detailed Price Chart` : 'Price Chart'}
        visible={chartModalVisible}
        onCancel={() => {
          setChartModalVisible(false)
          setSelectedNode(null)
        }}
        footer={null}
        width={800}
        style={{ top: 50 }}
      >
        {selectedNode && (
          <div style={{ height: 400, background: '#1a1a1a', borderRadius: 8, padding: 16 }}>
            <div style={{ marginBottom: 16 }}>
              <Title level={4} style={{ color: '#ffffff', margin: 0 }}>
                {selectedNode.node_name}
              </Title>
              <Text style={{ color: '#cccccc', fontSize: 12 }}>
                Last 24 hours • Real-Time vs Day-Ahead
              </Text>
            </div>
            
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={(() => {
                const hours = 24
                const now = new Date()
                const data = []
                
                for (let i = hours; i >= 0; i--) {
                  const time = new Date(now.getTime() - i * 60 * 60 * 1000)
                  const basePrice = selectedNode.current_price || 45
                  const volatility = (Math.random() - 0.5) * 10
                  const price = Math.max(15, basePrice + volatility)
                  
                  data.push({
                    time: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    price: Number(price.toFixed(2)),
                    da_price: Number((price + (Math.random() - 0.5) * 5).toFixed(2))
                  })
                }
                return data
              })()}>
                <Line 
                  type="monotone" 
                  dataKey="price" 
                  stroke="#00cc00" 
                  strokeWidth={2}
                  name="Real-Time"
                  dot={false}
                />
                <Line 
                  type="monotone" 
                  dataKey="da_price" 
                  stroke="#0066ff" 
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  name="Day-Ahead"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
            
            <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ width: 12, height: 2, background: '#00cc00', marginRight: 8 }}></div>
                <Text style={{ color: '#cccccc', fontSize: 12 }}>Real-Time</Text>
              </div>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ width: 12, height: 2, background: '#0066ff', marginRight: 8 }}></div>
                <Text style={{ color: '#cccccc', fontSize: 12 }}>Day-Ahead</Text>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Modals */}
      <AddToWatchlistModal
        visible={addModalVisible}
        onClose={() => setAddModalVisible(false)}
        onAdd={handleAddToWatchlist}
        availableNodes={mockAvailableNodes}
        loading={false}
      />
    </div>
  )
}

export default WatchlistDashboard
