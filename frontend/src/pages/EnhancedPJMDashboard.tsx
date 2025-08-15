import React, { useState, useEffect } from 'react'
import {
  Card,
  Space,
  Typography,
  Button,
  Tag,
  Badge,
  Alert,
  Tooltip,
  Switch,
  Modal,
  Progress,
  Descriptions
} from '@arco-design/web-react'
import {
  IconInfoCircle,
  IconCheckCircle,
  IconEye,
  IconUp,
  IconDown,
  IconRefresh,
  IconFire,
  IconExclamationCircle
} from '@arco-design/web-react/icon'

const { Title, Text } = Typography

// Industry-standard price formatter
const formatElectricityPrice = (price, options = {}) => {
  const { showUnit = true, precision = 2 } = options

  let formattedValue, colorStyle

  if (price < 0) {
    // Industry convention: Blue/Purple for negative prices
    formattedValue = `−$${Math.abs(price).toFixed(precision)}`
    colorStyle = {
      color: '#6366f1',  // Indigo (industry standard)
      fontWeight: 600,
      textShadow: '0 0 2px rgba(99, 102, 241, 0.3)'
    }
  } else if (price > 100) {
    // Price spikes: Orange/Red
    formattedValue = `$${price.toFixed(precision)}`
    colorStyle = {
      color: '#ef4444',
      fontWeight: 700,
      textShadow: '0 0 3px rgba(239, 68, 68, 0.4)'
    }
  } else {
    formattedValue = `$${price.toFixed(precision)}`
    colorStyle = { color: '#ffffff', fontWeight: 600 }
  }

  return {
    value: formattedValue + (showUnit ? '/MWh' : ''),
    style: colorStyle
  }
}

// LMP Component Bar showing % breakdown
const LMPComponentBar = ({ energyComponent, congestionComponent, lossComponent, totalLMP, width = 80 }) => {
  const total = Math.abs(energyComponent) + Math.abs(congestionComponent) + Math.abs(lossComponent)
  
  if (total === 0) return null
  
  const energyPct = (Math.abs(energyComponent) / total) * 100
  const congestionPct = (Math.abs(congestionComponent) / total) * 100
  const lossPct = (Math.abs(lossComponent) / total) * 100
  
  return (
    <Tooltip
      content={
        <div style={{ fontSize: 11 }}>
          <div style={{ marginBottom: 4, fontWeight: 600 }}>
            LMP Breakdown: {formatElectricityPrice(totalLMP).value}
          </div>
          <div style={{ color: '#10b981', marginBottom: 2 }}>
            Energy: ${energyComponent.toFixed(2)} ({energyPct.toFixed(1)}%)
          </div>
          <div style={{ color: congestionComponent >= 0 ? '#f59e0b' : '#ef4444', marginBottom: 2 }}>
            Congestion: {congestionComponent >= 0 ? '+' : ''}${congestionComponent.toFixed(2)} ({congestionPct.toFixed(1)}%)
          </div>
          <div style={{ color: '#f97316' }}>
            Losses: ${lossComponent.toFixed(2)} ({lossPct.toFixed(1)}%)
          </div>
        </div>
      }
    >
      <div style={{
        width: width,
        height: 16,
        display: 'flex',
        borderRadius: 3,
        overflow: 'hidden',
        border: '1px solid #444',
        cursor: 'pointer'
      }}>
        <div style={{ width: `${energyPct}%`, background: '#10b981', opacity: 0.8 }} />
        <div style={{ width: `${congestionPct}%`, background: congestionComponent >= 0 ? '#f59e0b' : '#ef4444', opacity: 0.8 }} />
        <div style={{ width: `${lossPct}%`, background: '#f97316', opacity: 0.8 }} />
      </div>
    </Tooltip>
  )
}

// Constraint drill-down modal
const ConstraintDrillDownModal = ({ visible, onClose, node }) => {
  if (!node) return null

  const mockConstraints = [
    {
      name: "AP South Interface",
      type: "interface", 
      status: "binding",
      limitMW: 1850,
      actualFlowMW: 1847.5,
      utilizationPercent: 99.8,
      shadowPrice: 15.75,
      description: "Interface constraint between AP South region and rest of PJM"
    }
  ]

  return (
    <Modal
      title={`${node.ticker_symbol} - Transmission Constraints`}
      visible={visible}
      onCancel={onClose}
      footer={null}
      width={700}
    >
      <div style={{ background: '#1a1a1a', padding: 16, borderRadius: 8 }}>
        <Alert
          type="warning"
          content={`${mockConstraints.length} active constraints affecting this node`}
          style={{ marginBottom: 16, background: 'rgba(245, 158, 11, 0.1)', borderColor: '#f59e0b', color: '#ffffff' }}
        />
        
        {mockConstraints.map((constraint, i) => (
          <Card key={i} style={{ marginBottom: 12, background: 'rgba(255, 255, 255, 0.03)', border: '1px solid #444' }}>
            <div style={{ marginBottom: 12 }}>
              <Title level={6} style={{ color: '#ffffff', margin: 0 }}>
                {constraint.name}
              </Title>
              <Text style={{ fontSize: 11, color: '#cccccc' }}>
                {constraint.description}
              </Text>
            </div>
            
            <div style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <Text style={{ fontSize: 12, color: '#cccccc' }}>Power Flow</Text>
                <Text style={{ fontSize: 12, color: '#ffffff' }}>
                  {constraint.actualFlowMW} / {constraint.limitMW} MW
                </Text>
              </div>
              <Progress
                percent={constraint.utilizationPercent}
                status={constraint.utilizationPercent >= 100 ? 'danger' : constraint.utilizationPercent >= 95 ? 'warning' : 'normal'}
                showText={false}
                strokeWidth={6}
              />
            </div>
            
            <div style={{ display: 'flex', gap: 16 }}>
              <Badge count={constraint.status.toUpperCase()} style={{ background: '#f59e0b' }} />
              <Badge count={`$${constraint.shadowPrice}/MWh`} style={{ background: '#8b5cf6' }} />
            </div>
          </Card>
        ))}
      </div>
    </Modal>
  )
}

// Enhanced node ticker with all improvements
const SuperEnhancedNodeTicker = ({ node, onViewChart, showDecomposition, onConstraintClick }) => {
  const priceInfo = formatElectricityPrice(node.current_price)
  const isPositive = (node.price_change_5min || 0) >= 0
  const hasConstraints = node.transmission_constraints?.has_constraints || false
  
  // Calculate spread vs PJM RTO Hub
  const hubSpread = node.current_price - (node.hub_spreads?.PJM_RTO?.hub_price || node.current_price)
  const hubSpreadInfo = formatElectricityPrice(hubSpread, { showUnit: false })

  return (
    <div 
      style={{
        padding: '16px',
        border: '1px solid #444',
        borderRadius: '8px',
        background: 'rgba(255, 255, 255, 0.03)',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        marginBottom: '8px',
        position: 'relative'
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
      {/* Constraint badge with click handler */}
      {hasConstraints && (
        <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 2 }}>
          <Tag
            style={{
              background: node.transmission_constraints.color,
              color: '#ffffff',
              border: 'none',
              fontSize: '9px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
            icon={<IconFire style={{ fontSize: 10 }} />}
            onClick={(e) => {
              e.stopPropagation()
              onConstraintClick(node)
            }}
          >
            CONSTRAINED
          </Tag>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        {/* Left side */}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <Text style={{ fontWeight: 700, fontSize: 16, fontFamily: 'monospace', color: '#ffffff' }}>
              {node.ticker_symbol}
            </Text>
            
            {/* Negative price indicator */}
            {node.current_price < 0 && (
              <Badge
                count="NEGATIVE LMP"
                style={{
                  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  color: '#ffffff',
                  fontSize: 9,
                  border: '1px solid #6366f1'
                }}
              />
            )}
          </div>
          
          <Text style={{ fontSize: 12, color: '#cccccc' }}>
            {node.node_name}
          </Text>
          
          {/* Hub spread indicator */}
          <div style={{ marginTop: 4 }}>
            <Text style={{ 
              fontSize: 10,
              color: Math.abs(hubSpread) > 5 ? '#ffaa44' : '#cccccc'
            }}>
              vs RTO Hub: <span style={hubSpreadInfo.style}>{hubSpreadInfo.value}</span>
              {Math.abs(hubSpread) > 10 && (
                <Badge count="ARBITRAGE" style={{ marginLeft: 4, background: '#8b5cf6', fontSize: 8 }} />
              )}
            </Text>
          </div>
        </div>

        {/* Center - Component bar */}
        <div style={{ margin: '0 16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          {showDecomposition && node.price_decomposition ? (
            <LMPComponentBar
              energyComponent={node.price_decomposition.energy}
              congestionComponent={node.price_decomposition.congestion}
              lossComponent={node.price_decomposition.losses}
              totalLMP={node.current_price}
              width={90}
            />
          ) : (
            <div style={{ width: 90, height: 16, background: '#333', borderRadius: 3 }} />
          )}
          
          <Text style={{ fontSize: 8, color: '#666', marginTop: 2 }}>
            {showDecomposition ? 'E•C•L' : 'Components'}
          </Text>
        </div>

        {/* Right side - Enhanced price display */}
        <div style={{ textAlign: 'right', minWidth: 120 }}>
          <div style={{
            fontSize: 18,
            fontWeight: 700,
            fontFamily: 'monospace',
            ...priceInfo.style
          }}>
            {priceInfo.value}
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
              {isPositive ? '+' : ''}{(node.price_change_5min || 0).toFixed(2)} ({(node.price_change_percent || 0).toFixed(1)}%)
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

// Main enhanced dashboard with all improvements
const EnhancedPJMDashboard = () => {
  const [showDecomposition, setShowDecomposition] = useState(true)
  const [showHeatmap, setShowHeatmap] = useState(false)
  const [constraintModalVisible, setConstraintModalVisible] = useState(false)
  const [selectedNode, setSelectedNode] = useState(null)
  
  // Enhanced mock data with all features
  const mockNodes = [
    {
      node_id: 1,
      ticker_symbol: "PJMRTO",
      node_name: "PJM RTO Hub",
      pnode_id: "51217",
      current_price: 42.75,
      price_change_5min: 1.25,
      price_change_percent: 3.01,
      day_ahead_price: 41.50,
      data_quality: 'provisional_complete',
      transmission_constraints: {
        has_constraints: true,
        constraint_count: 2,
        color: '#ff6600',
        constraint_names: ['AP South Interface', '5004/5005 Interface']
      },
      price_decomposition: {
        energy: 38.20,
        congestion: 3.15,
        losses: 1.40
      },
      hub_spreads: {
        PJM_RTO: { hub_price: 42.75, spread: 0 },
        WESTERN_HUB: { hub_price: 40.50, spread: 2.25 }
      },
      last_updated: new Date().toISOString()
    },
    {
      node_id: 2,
      ticker_symbol: "KNY138T61",
      node_name: "Kearneys 138 KV T61", 
      pnode_id: "54891230",
      current_price: -5.25,  // Negative price with industry blue styling
      price_change_5min: -8.50,
      price_change_percent: -61.8,
      day_ahead_price: 44.25,
      data_quality: 'verified_complete',
      transmission_constraints: {
        has_constraints: false
      },
      price_decomposition: {
        energy: 15.20,
        congestion: -22.75,  // High negative congestion causing negative LMP
        losses: 2.30
      },
      hub_spreads: {
        PJM_RTO: { hub_price: 42.75, spread: -48.00 },
        WESTERN_HUB: { hub_price: 40.50, spread: -45.75 }
      },
      last_updated: new Date().toISOString()
    },
    {
      node_id: 3,
      ticker_symbol: "WESTUB",
      node_name: "Western Hub",
      pnode_id: "52011", 
      current_price: 145.60,  // Price spike
      price_change_5min: 67.80,
      price_change_percent: 87.2,
      day_ahead_price: 39.20,
      data_quality: 'provisional_partial',
      transmission_constraints: {
        has_constraints: true,
        constraint_count: 1,
        color: '#ff0000',
        constraint_names: ['Western Interface']
      },
      price_decomposition: {
        energy: 55.80,
        congestion: 85.50,  // Very high congestion causing spike
        losses: 4.30
      },
      hub_spreads: {
        PJM_RTO: { hub_price: 42.75, spread: 102.85 },
        WESTERN_HUB: { hub_price: 145.60, spread: 0 }
      },
      last_updated: new Date().toISOString()
    }
  ]

  const handleConstraintClick = (node) => {
    setSelectedNode(node)
    setConstraintModalVisible(true)
  }

  const handleViewChart = (node) => {
    Message.info(`Opening detailed chart for ${node.ticker_symbol}`)
  }

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '16px' }}>
      {/* Market status banner */}
      <Alert
        type="warning"
        content="⚠️ MARKET WARNING: RT data feed delayed by 12 minutes - Last update: 08:12 PM EST"
        style={{
          marginBottom: 20,
          background: 'rgba(255, 170, 0, 0.1)',
          borderColor: '#ffaa00',
          color: '#ffffff'
        }}
        showIcon
      />
      
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ color: '#ffffff', marginBottom: 8 }}>
          ⚡ Enhanced PJM Dashboard
        </Title>
        
        <Text style={{ color: '#cccccc', marginBottom: 16 }}>
          Industry-standard negative pricing • Component bars • Constraint drill-down • Hub spreads
        </Text>

        {/* Controls */}
        <div style={{ display: 'flex', gap: 20, marginBottom: 20 }}>
          <Space>
            <Switch checked={showDecomposition} onChange={setShowDecomposition} size="small" />
            <Text style={{ color: '#ffffff', fontSize: 12 }}>Component % Bars</Text>
          </Space>
          <Space>
            <Switch checked={showHeatmap} onChange={setShowHeatmap} size="small" />
            <Text style={{ color: '#ffffff', fontSize: 12 }}>Heatmap View</Text>
          </Space>
        </div>

        {/* Enhanced stats */}
        <div style={{ display: 'flex', gap: 20, marginBottom: 20 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#6366f1' }}>
              1
            </div>
            <Text style={{ fontSize: 11, color: '#cccccc' }}>Negative LMP</Text>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#ef4444' }}>
              1
            </div>
            <Text style={{ fontSize: 11, color: '#cccccc' }}>Price Spike</Text>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#ff6600' }}>
              2
            </div>
            <Text style={{ fontSize: 11, color: '#cccccc' }}>Constrained</Text>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#8b5cf6' }}>
              1
            </div>
            <Text style={{ fontSize: 11, color: '#cccccc' }}>Arbitrage Opp</Text>
          </div>
        </div>
      </div>

      {/* Heatmap view */}
      {showHeatmap && (
        <Card style={{ 
          marginBottom: 20,
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid #333'
        }}>
          <Title level={5} style={{ color: '#ffffff', marginBottom: 12 }}>
            📊 Price Change Heatmap
          </Title>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {mockNodes.map((node, i) => {
              const intensity = Math.abs(node.price_change_percent) / 100
              let color
              
              if (node.current_price < 0) {
                color = `rgba(99, 102, 241, ${0.3 + intensity * 0.7})`  // Blue for negative
              } else if (node.price_change_percent >= 0) {
                color = `rgba(16, 185, 129, ${0.3 + intensity * 0.7})`  // Green for positive
              } else {
                color = `rgba(239, 68, 68, ${0.3 + intensity * 0.7})`   // Red for declining
              }
              
              const priceFormatted = formatElectricityPrice(node.current_price)
              
              return (
                <div key={i} style={{
                  padding: '16px',
                  background: color,
                  border: `2px solid ${node.current_price < 0 ? '#6366f1' : node.price_change_percent >= 0 ? '#10b981' : '#ef4444'}`,
                  borderRadius: 8,
                  textAlign: 'center',
                  cursor: 'pointer'
                }}>
                  <div style={{ fontWeight: 700, color: '#ffffff', fontSize: 16 }}>
                    {node.ticker_symbol}
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 700, margin: '8px 0', ...priceFormatted.style }}>
                    {priceFormatted.value}
                  </div>
                  <div style={{ 
                    fontSize: 14, 
                    color: node.current_price < 0 ? '#6366f1' : node.price_change_percent >= 0 ? '#10b981' : '#ef4444'
                  }}>
                    {node.price_change_percent >= 0 ? '+' : ''}{node.price_change_percent.toFixed(1)}%
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Enhanced node list */}
      <Card style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid #333' }}>
        <div style={{ padding: '16px 16px 8px 16px' }}>
          <Title level={4} style={{ color: '#ffffff', marginBottom: 12 }}>
            Enhanced PJM Nodes
          </Title>
          
          {/* Feature legend */}
          <div style={{ 
            display: 'flex', 
            gap: 12, 
            marginBottom: 16,
            padding: 12,
            background: 'rgba(255, 255, 255, 0.02)',
            borderRadius: 4,
            border: '1px solid #333'
          }}>
            <Badge count="NEGATIVE $" style={{ background: '#6366f1', fontSize: 9 }} />
            <Badge count="COMPONENT %" style={{ background: '#10b981', fontSize: 9 }} />
            <Badge count="CONSTRAINTS" style={{ background: '#ff6600', fontSize: 9 }} />
            <Badge count="HUB SPREADS" style={{ background: '#8b5cf6', fontSize: 9 }} />
          </div>
        </div>
        
        <div style={{ padding: '0 8px 8px 8px' }}>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            {mockNodes.map(node => (
              <SuperEnhancedNodeTicker
                key={node.node_id}
                node={node}
                onViewChart={handleViewChart}
                showDecomposition={showDecomposition}
                onConstraintClick={handleConstraintClick}
              />
            ))}
          </Space>
        </div>
      </Card>

      {/* Hub spread analysis */}
      <Card style={{ 
        marginTop: 20,
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid #333'
      }}>
        <Title level={5} style={{ color: '#ffffff', marginBottom: 12 }}>
          📊 Hub Spread Analysis
        </Title>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {mockNodes.map((node, i) => {
            const rtoPremium = node.hub_spreads?.PJM_RTO?.spread || 0
            const westernPremium = node.hub_spreads?.WESTERN_HUB?.spread || 0
            
            return (
              <div key={i} style={{
                padding: '12px',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid #444',
                borderRadius: 6
              }}>
                <div style={{ fontWeight: 600, color: '#ffffff', marginBottom: 8 }}>
                  {node.ticker_symbol}
                </div>
                
                <div style={{ fontSize: 11, lineHeight: 1.4 }}>
                  <div style={{ marginBottom: 4 }}>
                    <span style={{ color: '#cccccc' }}>vs RTO Hub: </span>
                    <span style={{
                      color: Math.abs(rtoPremium) > 10 ? '#ffaa44' : '#cccccc',
                      fontWeight: Math.abs(rtoPremium) > 10 ? 600 : 400
                    }}>
                      {rtoPremium > 0 ? '+' : ''}${rtoPremium.toFixed(2)}/MWh
                    </span>
                  </div>
                  
                  <div style={{ marginBottom: 4 }}>
                    <span style={{ color: '#cccccc' }}>vs West Hub: </span>
                    <span style={{
                      color: Math.abs(westernPremium) > 10 ? '#ffaa44' : '#cccccc',
                      fontWeight: Math.abs(westernPremium) > 10 ? 600 : 400
                    }}>
                      {westernPremium > 0 ? '+' : ''}${westernPremium.toFixed(2)}/MWh
                    </span>
                  </div>
                  
                  {Math.abs(rtoPremium) > 10 && (
                    <Badge
                      count="ARBITRAGE OPP"
                      style={{
                        background: '#8b5cf6',
                        fontSize: 8,
                        marginTop: 4
                      }}
                    />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      {/* Feature showcase */}
      <Alert
        type="success"
        content={
          <div>
            <strong>✅ All Enhanced Features Active:</strong>
            <br />• Industry-standard negative price highlighting (blue/purple)
            <br />• Component % bars showing Energy/Congestion/Loss breakdown
            <br />• Clickable constraint badges with drill-down details
            <br />• Hub spread analysis for relative value trading
            <br />• Heatmap visualization and data quality monitoring
          </div>
        }
        style={{
          marginTop: 20,
          background: 'rgba(0, 204, 0, 0.1)',
          borderColor: '#00cc00',
          color: '#ffffff'
        }}
      />

      {/* Constraint drill-down modal */}
      <ConstraintDrillDownModal
        visible={constraintModalVisible}
        onClose={() => {
          setConstraintModalVisible(false)
          setSelectedNode(null)
        }}
        node={selectedNode}
      />
    </div>
  )
}

export default EnhancedPJMDashboard
