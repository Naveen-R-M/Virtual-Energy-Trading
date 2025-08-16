import React, { useState, useEffect } from 'react'
import { Alert, Badge, Button, Space, Tooltip, Progress } from '@arco-design/web-react'
import {
  IconClockCircle,
  IconExclamationCircle,
  IconCheckCircle,
  IconRefresh,
  IconInfoCircle
} from '@arco-design/web-react/icon'

interface TradingStateInfo {
  state: string
  timestamp_et: string
  permissions: {
    da_orders: boolean
    rt_orders: boolean
  }
  next_transition: {
    next_state: string
    seconds_until: number
    human_readable: string
  }
  feature_enabled: boolean
}

interface MarketStatusBannerProps {
  onRefresh?: () => void
  className?: string
}

const MarketStatusBanner: React.FC<MarketStatusBannerProps> = ({ 
  onRefresh,
  className = ''
}) => {
  const [tradingState, setTradingState] = useState<TradingStateInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [feedAge, setFeedAge] = useState(0)

  // Mock data - in real app, fetch from /api/market/trading-state
  const mockTradingState: TradingStateInfo = {
    state: "PRE_11AM",
    timestamp_et: new Date().toISOString(),
    permissions: {
      da_orders: true,
      rt_orders: true
    },
    next_transition: {
      next_state: "POST_11AM",
      seconds_until: 2847, // ~47 minutes
      human_readable: "47m 27s"
    },
    feature_enabled: true
  }

  useEffect(() => {
    fetchTradingState()
    
    // Update every 30 seconds
    const interval = setInterval(() => {
      fetchTradingState()
      updateFeedAge()
    }, 30000)
    
    return () => clearInterval(interval)
  }, [])

  const fetchTradingState = async () => {
    try {
      // In real implementation:
      // const response = await fetch('/api/market/trading-state')
      // const data = await response.json()
      
      // For now, use mock data
      setTradingState(mockTradingState)
      setLastUpdate(new Date())
      setLoading(false)
    } catch (error) {
      console.error('Error fetching trading state:', error)
      setLoading(false)
    }
  }

  const updateFeedAge = () => {
    const now = new Date()
    const ageSeconds = Math.floor((now.getTime() - lastUpdate.getTime()) / 1000)
    setFeedAge(ageSeconds)
  }

  const getStateDisplay = (state: string) => {
    const stateConfig = {
      PRE_MARKET: {
        color: '#666666',
        text: 'PRE-MARKET',
        icon: <IconClockCircle />,
        description: 'Market opening soon'
      },
      PRE_11AM: {
        color: '#00cc00',
        text: 'DA OPEN',
        icon: <IconCheckCircle />,
        description: 'Day-ahead orders accepted'
      },
      POST_11AM: {
        color: '#ff6600',
        text: 'DA CLOSED',
        icon: <IconExclamationCircle />,
        description: 'RT orders only'
      },
      END_OF_DAY: {
        color: '#ff4d4f',
        text: 'MARKET CLOSED',
        icon: <IconExclamationCircle />,
        description: 'Trading day ended'
      }
    }

    return stateConfig[state as keyof typeof stateConfig] || {
      color: '#999999',
      text: 'UNKNOWN',
      icon: <IconInfoCircle />,
      description: 'Unknown state'
    }
  }

  const formatCountdown = (seconds: number): string => {
    if (seconds <= 0) return 'Now'
    
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`
    } else {
      return `${secs}s`
    }
  }

  const isStaleData = feedAge > 600 // 10 minutes
  const isVeryStale = feedAge > 1800 // 30 minutes

  if (loading) {
    return (
      <Alert
        type="info"
        content="Loading market status..."
        style={{ marginBottom: 16 }}
        showIcon
      />
    )
  }

  if (!tradingState) {
    return (
      <Alert
        type="error"
        content="Unable to load market status"
        style={{ marginBottom: 16 }}
        showIcon
      />
    )
  }

  // Feature flag disabled - show legacy notice
  if (!tradingState.feature_enabled) {
    return (
      <Alert
        type="info"
        content="🔧 Legacy mode - PJM state machine disabled. DA orders use basic 11am cutoff."
        style={{ marginBottom: 16 }}
        showIcon
      />
    )
  }

  const stateDisplay = getStateDisplay(tradingState.state)

  // Stale data warning
  if (isStaleData) {
    return (
      <Alert
        type={isVeryStale ? "error" : "warning"}
        content={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>
              {isVeryStale ? '🔴' : '⚠️'} Market data feed delayed by {Math.floor(feedAge / 60)} minutes
              - Last update: {lastUpdate.toLocaleTimeString()}
            </span>
            <Button 
              size="small" 
              type="primary" 
              icon={<IconRefresh />}
              onClick={() => {
                fetchTradingState()
                if (onRefresh) onRefresh()
              }}
            >
              Refresh
            </Button>
          </div>
        }
        style={{ marginBottom: 16 }}
        showIcon
      />
    )
  }

  // DA closed banner
  if (tradingState.state === 'POST_11AM') {
    return (
      <Alert
        type="warning"
        content={
          <div>
            <Space align="center">
              <Badge 
                count={stateDisplay.text}
                style={{ 
                  background: stateDisplay.color,
                  color: '#ffffff',
                  fontWeight: 600
                }}
              />
              <span>
                Day-ahead market closed until tomorrow 11:00 AM ET
              </span>
              <Tooltip content={`Market transitions to ${tradingState.next_transition.next_state} in ${tradingState.next_transition.human_readable}`}>
                <IconInfoCircle style={{ color: '#666', cursor: 'help' }} />
              </Tooltip>
            </Space>
            
            <div style={{ marginTop: 8 }}>
              <span style={{ fontSize: 12, color: '#666' }}>
                RT orders still available • Next DA window: {formatCountdown(tradingState.next_transition.seconds_until)}
              </span>
            </div>
          </div>
        }
        style={{ marginBottom: 16 }}
        showIcon
      />
    )
  }

  // Normal market status display
  return (
    <div className={`market-status-banner ${className}`} style={{ marginBottom: 16 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          background: 'rgba(255, 255, 255, 0.03)',
          border: `1px solid ${stateDisplay.color}`,
          borderRadius: 6,
          backdropFilter: 'blur(4px)'
        }}
      >
        <Space align="center">
          <Badge 
            count={stateDisplay.text}
            style={{ 
              background: stateDisplay.color,
              color: '#ffffff',
              fontWeight: 600,
              fontSize: 11
            }}
          />
          
          <span style={{ color: '#ffffff', fontWeight: 500 }}>
            {stateDisplay.description}
          </span>
          
          {tradingState.permissions.da_orders && (
            <Badge count="DA OK" style={{ background: '#00cc00', fontSize: 9 }} />
          )}
          {tradingState.permissions.rt_orders && (
            <Badge count="RT OK" style={{ background: '#0066ff', fontSize: 9 }} />
          )}
        </Space>

        <Space align="center">
          {tradingState.state === 'PRE_11AM' && (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 13, color: '#ffaa00', fontWeight: 600 }}>
                DA closes in {formatCountdown(tradingState.next_transition.seconds_until)}
              </div>
              <div style={{ fontSize: 10, color: '#cccccc' }}>
                {new Date(tradingState.timestamp_et).toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit',
                  second: '2-digit',
                  timeZoneName: 'short'
                })}
              </div>
            </div>
          )}
          
          <Tooltip content="Refresh market status">
            <Button
              type="text"
              size="small"
              icon={<IconRefresh style={{ color: '#cccccc' }} />}
              onClick={() => {
                fetchTradingState()
                if (onRefresh) onRefresh()
              }}
              style={{ color: '#cccccc' }}
            />
          </Tooltip>
        </Space>
      </div>
      
      {/* Countdown progress bar for PRE_11AM */}
      {tradingState.state === 'PRE_11AM' && tradingState.next_transition.seconds_until < 3600 && (
        <div style={{ marginTop: 8 }}>
          <Progress
            percent={Math.max(0, 100 - (tradingState.next_transition.seconds_until / 3600 * 100))}
            status="normal"
            showText={false}
            strokeWidth={3}
            trailColor="#333"
            color={{
              '0%': '#00cc00',
              '70%': '#ffaa00', 
              '90%': '#ff6600',
              '100%': '#ff4d4f'
            }}
          />
          <div style={{ 
            fontSize: 10, 
            color: '#cccccc', 
            textAlign: 'center',
            marginTop: 2
          }}>
            DA Market Countdown
          </div>
        </div>
      )}
    </div>
  )
}

export default MarketStatusBanner