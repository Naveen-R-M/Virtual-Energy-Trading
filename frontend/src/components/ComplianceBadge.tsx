import React from 'react'
import { Badge, Tooltip } from '@arco-design/web-react'
import {
  IconCheckCircle,
  IconClockCircle,
  IconExclamationCircle,
  IconInfoCircle
} from '@arco-design/web-react/icon'

export interface DataQualityStatus {
  type: 'verified' | 'provisional' | 'partial' | 'unknown'
  settlement_status?: 'final_verified' | 'provisional_intraday' | 'incomplete'
  data_source?: string
  intervals_verified?: number
  total_intervals?: number
  settlement_difference?: number
  last_updated?: string
}

interface ComplianceBadgeProps {
  status: DataQualityStatus
  size?: 'small' | 'default' | 'large'
  showIcon?: boolean
  detailed?: boolean
  className?: string
}

const ComplianceBadge: React.FC<ComplianceBadgeProps> = ({
  status,
  size = 'default',
  showIcon = true,
  detailed = false,
  className = ''
}) => {
  const getBadgeConfig = () => {
    switch (status.type) {
      case 'verified':
        return {
          color: '#00cc00',
          text: detailed ? 'VERIFIED' : 'V',
          icon: <IconCheckCircle style={{ fontSize: 10 }} />,
          tooltip: getVerifiedTooltip()
        }
      
      case 'provisional':
        return {
          color: '#0066ff', 
          text: detailed ? 'PROVISIONAL' : 'P',
          icon: <IconClockCircle style={{ fontSize: 10 }} />,
          tooltip: getProvisionalTooltip()
        }
      
      case 'partial':
        return {
          color: '#ffaa00',
          text: detailed ? 'PARTIAL' : '~',
          icon: <IconExclamationCircle style={{ fontSize: 10 }} />,
          tooltip: getPartialTooltip()
        }
      
      case 'unknown':
      default:
        return {
          color: '#666666',
          text: detailed ? 'UNKNOWN' : '?',
          icon: <IconInfoCircle style={{ fontSize: 10 }} />,
          tooltip: 'Data quality unknown'
        }
    }
  }

  const getVerifiedTooltip = () => {
    const lines = ['✅ Final verified settlement data']
    
    if (status.settlement_status === 'final_verified') {
      lines.push('• T+2 verified settlement prices')
    }
    
    if (status.data_source) {
      lines.push(`• Source: ${status.data_source}`)
    }
    
    if (status.settlement_difference && Math.abs(status.settlement_difference) > 0.01) {
      const diff = status.settlement_difference
      lines.push(`• Revision: ${diff > 0 ? '+' : ''}$${diff.toFixed(2)} vs provisional`)
    }
    
    if (status.last_updated) {
      lines.push(`• Updated: ${new Date(status.last_updated).toLocaleTimeString()}`)
    }
    
    return (
      <div style={{ fontSize: 11, lineHeight: 1.4 }}>
        {lines.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </div>
    )
  }

  const getProvisionalTooltip = () => {
    const lines = ['⏳ Using real-time provisional data']
    
    if (status.settlement_status === 'provisional_intraday') {
      lines.push('• Intraday real-time prices')
      lines.push('• Final P&L pending verified settlement')
    }
    
    if (status.data_source) {
      lines.push(`• Source: ${status.data_source}`)
    }
    
    if (status.intervals_verified && status.total_intervals) {
      const percent = (status.intervals_verified / status.total_intervals * 100).toFixed(1)
      lines.push(`• Coverage: ${status.intervals_verified}/${status.total_intervals} intervals (${percent}%)`)
    }
    
    lines.push('• Will update to verified data at T+2 days')
    
    return (
      <div style={{ fontSize: 11, lineHeight: 1.4 }}>
        {lines.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </div>
    )
  }

  const getPartialTooltip = () => {
    const lines = ['⚠️ Incomplete data - some intervals missing']
    
    if (status.intervals_verified && status.total_intervals) {
      const missing = status.total_intervals - status.intervals_verified
      const percent = (status.intervals_verified / status.total_intervals * 100).toFixed(1)
      lines.push(`• ${missing} missing out of ${status.total_intervals} intervals`)
      lines.push(`• Coverage: ${percent}%`)
    } else {
      lines.push('• Some 5-minute buckets have missing RT prices')
    }
    
    if (status.settlement_status === 'incomplete') {
      lines.push('• P&L calculation may be inaccurate')
      lines.push('• Missing intervals excluded from settlement')
    }
    
    if (status.data_source) {
      lines.push(`• Source: ${status.data_source}`)
    }
    
    return (
      <div style={{ fontSize: 11, lineHeight: 1.4 }}>
        {lines.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </div>
    )
  }

  const config = getBadgeConfig()
  
  const badgeStyle = {
    background: config.color,
    color: '#ffffff',
    fontSize: size === 'small' ? 8 : size === 'large' ? 12 : 10,
    fontWeight: 600,
    border: 'none',
    padding: size === 'small' ? '2px 4px' : size === 'large' ? '4px 8px' : '3px 6px',
    display: 'inline-flex',
    alignItems: 'center',
    gap: showIcon ? 3 : 0
  }

  const BadgeContent = () => (
    <span style={badgeStyle}>
      {showIcon && config.icon}
      {config.text}
    </span>
  )

  return (
    <Tooltip content={config.tooltip} mini={size === 'small'}>
      <div className={`compliance-badge ${className}`} style={{ display: 'inline-block' }}>
        <BadgeContent />
      </div>
    </Tooltip>
  )
}

// Convenience components for specific use cases
export const VerifiedBadge: React.FC<{ 
  size?: 'small' | 'default' | 'large'
  settlementDifference?: number
}> = ({ size, settlementDifference }) => (
  <ComplianceBadge 
    status={{ 
      type: 'verified', 
      settlement_status: 'final_verified',
      settlement_difference: settlementDifference,
      data_source: 'settlements_verified_5min'
    }} 
    size={size} 
  />
)

export const ProvisionalBadge: React.FC<{ 
  size?: 'small' | 'default' | 'large'
  intervalsVerified?: number
  totalIntervals?: number
}> = ({ size, intervalsVerified, totalIntervals }) => (
  <ComplianceBadge 
    status={{ 
      type: 'provisional', 
      settlement_status: 'provisional_intraday',
      intervals_verified: intervalsVerified,
      total_intervals: totalIntervals,
      data_source: 'real_time_5_min'
    }} 
    size={size}
  />
)

export const PartialBadge: React.FC<{ 
  size?: 'small' | 'default' | 'large'
  intervalsVerified?: number
  totalIntervals?: number
}> = ({ size, intervalsVerified, totalIntervals }) => (
  <ComplianceBadge 
    status={{ 
      type: 'partial', 
      settlement_status: 'incomplete',
      intervals_verified: intervalsVerified,
      total_intervals: totalIntervals,
      data_source: 'mixed_sources'
    }} 
    size={size}
  />
)

// Multi-badge display for showing progression (Provisional → Verified)
export const DataProgressionBadges: React.FC<{
  provisionalPnL: number
  verifiedPnL?: number
  dataQuality: 'provisional_only' | 'partially_verified' | 'fully_verified'
  size?: 'small' | 'default' | 'large'
}> = ({ provisionalPnL, verifiedPnL, dataQuality, size = 'default' }) => {
  const difference = verifiedPnL ? verifiedPnL - provisionalPnL : 0
  
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
      <ProvisionalBadge size={size} />
      
      {dataQuality !== 'provisional_only' && (
        <>
          <span style={{ color: '#666', fontSize: 8 }}>→</span>
          <VerifiedBadge size={size} settlementDifference={difference} />
        </>
      )}
      
      {Math.abs(difference) > 5 && (
        <Badge 
          count={`${difference > 0 ? '+' : ''}$${difference.toFixed(2)}`}
          style={{ 
            background: difference > 0 ? '#00cc00' : '#ff4d4f',
            fontSize: size === 'small' ? 8 : 9,
            marginLeft: 2
          }} 
        />
      )}
    </div>
  )
}

export default ComplianceBadge