import React, { useState } from 'react'
import { Card, Button, Typography, Space, Alert } from '@arco-design/web-react'
import { IconRefresh } from '@arco-design/web-react/icon'

const { Title, Text } = Typography

const HotReloadTest: React.FC = () => {
  const [lastUpdate, setLastUpdate] = useState(new Date().toLocaleTimeString())
  const [counter, setCounter] = useState(0)

  const updateTime = () => {
    setLastUpdate(new Date().toLocaleTimeString())
    setCounter(c => c + 1)
  }

  return (
    <Card
      className="webull-card"
      title="Development Tools"
      style={{ marginTop: 20 }}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Alert
          type="success"
          title="Hot Reload Active"
          content="Edit any component file to see instant updates"
        />
        
        <div style={{ 
          textAlign: 'center',
          padding: 20,
          background: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-primary)'
        }}>
          <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
            {counter}
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Test Counter • Last: {lastUpdate}
          </Text>
          
          <Button
            type="primary"
            icon={<IconRefresh />}
            onClick={updateTime}
            style={{ marginTop: 12 }}
            size="small"
          >
            Test Update
          </Button>
        </div>
        
        <Text type="secondary" style={{ fontSize: 11, textAlign: 'center' }}>
          Edit this component in src/components/HotReloadTest.tsx to test hot reload
        </Text>
      </Space>
    </Card>
  )
}

export default HotReloadTest
