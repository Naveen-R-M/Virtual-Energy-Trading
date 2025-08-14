import React from 'react'
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { Card, Layout, Typography, Avatar, Space, Button, Badge, Tabs, ConfigProvider } from '@arco-design/web-react'
import { 
  IconThunderbolt, 
  IconDashboard, 
  IconList, 
  IconSettings,
  IconUser,
  IconNotification
} from '@arco-design/web-react/icon'
import enUS from '@arco-design/web-react/es/locale/en-US'
import Dashboard from './pages/Dashboard'
import OrderManagement from './pages/OrderManagement'
import '@arco-design/web-react/dist/css/arco.css'
import './index.css'
import './webull-theme.css'

const { Header, Content } = Layout
const { Title, Text } = Typography
const TabPane = Tabs.TabPane

function AppContent() {
  const navigate = useNavigate()
  const location = useLocation()

  const tabItems = [
    {
      key: '/',
      icon: <IconDashboard />,
      title: 'Dashboard'
    },
    {
      key: '/orders',
      icon: <IconList />,
      title: 'Orders'
    },
    {
      key: '/settings',
      icon: <IconSettings />,
      title: 'Settings'
    }
  ]

  const handleTabChange = (key: string) => {
    navigate(key)
  }

  return (
    <Layout style={{ height: '100vh' }}>
      {/* Enhanced Header */}
      <Header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        height: 64,
        borderBottom: '1px solid var(--border-primary)'
      }}>
        {/* Brand & Title */}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <IconThunderbolt style={{ fontSize: 24, color: '#ffffff', marginRight: 16 }} />
          <div>
            <Title level={3} style={{ margin: 0, fontWeight: 700, fontSize: 18 }}>
              Energy Trader
            </Title>
            <Text type="secondary" style={{ fontSize: 11 }}>
              Virtual Energy Trading Platform • PJM_RTO
            </Text>
          </div>
        </div>

        <Space size="large">
          {/* Market Status */}
          <div className="market-status">
            <div className="status-dot success"></div>
            Market Open
          </div>

          {/* User Profile */}
          <Space>
            <Badge count={3} size="small">
              <IconNotification style={{ fontSize: 16, cursor: 'pointer' }} />
            </Badge>
            <Avatar size={32} style={{ background: '#ffffff', color: '#000000' }}>
              <IconUser />
            </Avatar>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>Demo Trader</div>
              <Text type="secondary" style={{ fontSize: 11 }}>
                Active Session
              </Text>
            </div>
          </Space>
        </Space>
      </Header>

      {/* Navigation Tabs */}
      <div style={{
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-primary)',
        padding: '0 24px'
      }}>
        <Tabs
          activeTab={location.pathname}
          onChange={handleTabChange}
          type="line"
          size="large"
          style={{ marginBottom: 0 }}
        >
          {tabItems.map(item => (
            <TabPane 
              key={item.key} 
              title={
                <Space>
                  {item.icon}
                  <span>{item.title}</span>
                </Space>
              }
            />
          ))}
        </Tabs>
      </div>

      {/* Content */}
      <Content style={{ padding: 24, overflow: 'auto', flex: 1 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/orders" element={<OrderManagement />} />
          <Route path="/settings" element={
            <Card className="webull-card" style={{ textAlign: 'center', padding: 60 }}>
              <div style={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                background: 'var(--accent-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px',
                fontSize: 24
              }}>
                ⚙️
              </div>
              <Title level={3} style={{ margin: 0 }}>Settings</Title>
              <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                Configuration options coming soon
              </Text>
              <Button 
                type="primary" 
                onClick={() => navigate('/')}
                style={{ marginTop: 20 }}
              >
                Back to Dashboard
              </Button>
            </Card>
          } />
        </Routes>
      </Content>
    </Layout>
  )
}

function App() {
  return (
    <ConfigProvider locale={enUS}>
      <Router>
        <AppContent />
      </Router>
    </ConfigProvider>
  )
}

export default App
