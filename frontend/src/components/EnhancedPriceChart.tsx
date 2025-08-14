import React, { useEffect, useRef, useState } from 'react';
import { Typography } from '@arco-design/web-react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  Brush,
} from 'recharts';
import dayjs from 'dayjs';

const { Text } = Typography;

/**
 * Duration configuration type
 */
type Duration = {
  key: string;
  label: string;
};

/**
 * Chart data point interface
 */
interface ChartDataPoint {
  timestamp: number;
  time: string;
  daPrice: number;
  rtPrice: number;
  spread: number;
  volume: number;
}

/**
 * Component props interface
 */
interface EnhancedPriceChartProps {
  loading?: boolean;
}

/**
 * Tooltip props interface
 */
interface TooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

/**
 * Generate comprehensive historical data for different time periods
 * @param duration - Time period (1d, 1w, 1m, 6m, 1y, 5y)
 * @returns Array of chart data points
 */
const generateHistoricalData = (duration: string): ChartDataPoint[] => {
  const data: ChartDataPoint[] = [];
  let startDate = dayjs();
  let intervals: number;
  let format: string;
  let intervalUnit: dayjs.ManipulateType;
  let intervalAmount: number;

  // Configure time parameters based on duration
  switch (duration) {
    case '1d':
      intervals = 24;
      format = 'HH:mm';
      intervalUnit = 'hour';
      intervalAmount = 1;
      startDate = startDate.startOf('day');
      break;
    case '1w':
      intervals = 7;
      format = 'MMM DD';
      intervalUnit = 'day';
      intervalAmount = 1;
      startDate = startDate.subtract(6, 'day');
      break;
    case '1m':
      intervals = 30;
      format = 'MMM DD';
      intervalUnit = 'day';
      intervalAmount = 1;
      startDate = startDate.subtract(29, 'day');
      break;
    case '6m':
      intervals = 26;
      format = 'MMM DD';
      intervalUnit = 'week';
      intervalAmount = 1;
      startDate = startDate.subtract(25, 'week');
      break;
    case '1y':
      intervals = 12;
      format = 'MMM YY';
      intervalUnit = 'month';
      intervalAmount = 1;
      startDate = startDate.subtract(11, 'month');
      break;
    case '5y':
      intervals = 5;
      format = 'YYYY';
      intervalUnit = 'year';
      intervalAmount = 1;
      startDate = startDate.subtract(4, 'year');
      break;
    default:
      intervals = 24;
      format = 'HH:mm';
      intervalUnit = 'hour';
      intervalAmount = 1;
      startDate = startDate.startOf('day');
  }

  // Generate realistic price data
  for (let i = 0; i < intervals; i++) {
    const timestamp = startDate.add(i * intervalAmount, intervalUnit);

    // Generate realistic price patterns based on time of day/period
    let basePrice = 45;
    let volatility = 0.15;

    if (duration === '1d') {
      // Intraday patterns with realistic energy market behavior
      const hour = timestamp.hour();
      if (hour >= 6 && hour <= 9) {
        // Morning ramp-up
        basePrice = 42 + (hour - 6) * 8;
        volatility = 0.25;
      } else if (hour >= 14 && hour <= 18) {
        // Peak demand hours
        basePrice = 68 + Math.sin((hour - 14) / 2) * 12;
        volatility = 0.3;
      } else if (hour >= 19 && hour <= 23) {
        // Evening decline
        basePrice = 52 - (hour - 19) * 4;
        volatility = 0.2;
      } else {
        // Off-peak hours
        basePrice = 32 + Math.sin(hour / 4) * 8;
        volatility = 0.1;
      }
    } else {
      // Longer-term patterns with seasonal and trend components
      const trend = Math.sin((i / intervals) * Math.PI * 2) * 20;
      const seasonal = Math.cos((i / intervals) * Math.PI * 4) * 10;
      basePrice = 50 + trend + seasonal;
      volatility = duration.includes('y') ? 0.4 : 0.25;
    }

    // Calculate day-ahead and real-time prices
    const daPrice = Math.max(15, basePrice + (Math.random() - 0.5) * basePrice * volatility);
    const rtPrice = Math.max(12, daPrice + (Math.random() - 0.5) * daPrice * 0.15);

    data.push({
      timestamp: timestamp.valueOf(),
      time: timestamp.format(format),
      daPrice: Math.round(daPrice * 100) / 100,
      rtPrice: Math.round(rtPrice * 100) / 100,
      spread: Math.round((rtPrice - daPrice) * 100) / 100,
      volume: Math.round(Math.random() * 1000 + 500),
    });
  }

  return data;
};

/**
 * Enhanced Price Chart Component with professional trading features
 * Includes time duration controls, mouse wheel zooming, and brush navigation
 */
const EnhancedPriceChart: React.FC<EnhancedPriceChartProps> = ({ loading = false }) => {
  // State management
  const [selectedDuration, setSelectedDuration] = useState<string>('1d');
  const [chartData, setChartData] = useState<ChartDataPoint[]>(generateHistoricalData('1d'));
  const [brushDomain, setBrushDomain] = useState<[number, number] | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  // Duration options configuration
  const durations: Duration[] = [
    { key: '1d', label: '1D' },
    { key: '1w', label: '1W' },
    { key: '1m', label: '1M' },
    { key: '6m', label: '6M' },
    { key: '1y', label: '1Y' },
    { key: '5y', label: '5Y' },
  ];

  // Update chart data when duration changes
  useEffect(() => {
    const newData = generateHistoricalData(selectedDuration);
    setChartData(newData);
    setBrushDomain(null); // Reset zoom when changing duration
  }, [selectedDuration]);

  // Mouse wheel zoom functionality
  useEffect(() => {
    const chartElement = chartRef.current;
    if (!chartElement) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();

      const rect = chartElement.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const chartWidth = rect.width;
      const mouseRatio = x / chartWidth;

      const dataLength = chartData.length;
      const currentStart = brushDomain ? brushDomain[0] : 0;
      const currentEnd = brushDomain ? brushDomain[1] : dataLength - 1;
      const currentRange = currentEnd - currentStart;

      const zoomFactor = e.deltaY > 0 ? 1.2 : 0.8; // Zoom out/in
      const newRange = Math.max(5, Math.min(dataLength, currentRange * zoomFactor));

      // Calculate new start/end based on mouse position
      const centerPoint = currentStart + (currentEnd - currentStart) * mouseRatio;
      let newStart = Math.round(centerPoint - newRange / 2);
      let newEnd = Math.round(centerPoint + newRange / 2);

      // Ensure bounds are within data limits
      if (newStart < 0) {
        newStart = 0;
        newEnd = newRange;
      } else if (newEnd >= dataLength) {
        newEnd = dataLength - 1;
        newStart = Math.max(0, newEnd - newRange);
      }

      setBrushDomain([newStart, newEnd]);
    };

    chartElement.addEventListener('wheel', handleWheel, { passive: false });
    return () => chartElement.removeEventListener('wheel', handleWheel);
  }, [chartData, brushDomain]);

  /**
   * Handle duration selection change
   */
  const handleDurationChange = (duration: string): void => {
    setSelectedDuration(duration);
  };

  /**
   * Handle brush domain changes for zooming/panning
   */
  const handleBrushChange = (domain: any): void => {
    if (domain?.startIndex !== undefined && domain?.endIndex !== undefined) {
      setBrushDomain([domain.startIndex, domain.endIndex]);
    }
  };

  /**
   * Custom tooltip component for chart hover information
   */
  const CustomTooltip: React.FC<TooltipProps> = ({ active, payload, label }) => {
    if (active && payload?.length) {
      return (
        <div className="custom-tooltip">
          <p
            style={{
              margin: 0,
              fontWeight: 600,
              fontSize: 12,
              color: '#ffffff',
            }}
          >
            {label}
          </p>
          {payload.map((entry: any, index: number) => (
            <p
              key={index}
              style={{
                margin: '4px 0',
                color: entry.color,
                fontWeight: 500,
                fontSize: 11,
              }}
            >
              {entry.name}: ${Number(entry.value).toFixed(2)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Get displayed data based on brush domain
  const displayData = brushDomain
    ? chartData.slice(brushDomain[0], brushDomain[1] + 1)
    : chartData;

  return (
    <div ref={chartRef} className="enhanced-chart-container">
      {/* Duration Controls */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <div className="duration-selector">
          {durations.map((duration) => (
            <button
              key={duration.key}
              className={`duration-button ${selectedDuration === duration.key ? 'active' : ''}`}
              onClick={() => handleDurationChange(duration.key)}
              type="button"
            >
              {duration.label}
            </button>
          ))}
        </div>

        <Text className="chart-instructions">Scroll to zoom • Drag timeline to pan</Text>
      </div>

      {/* Main Chart */}
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={displayData}>
          <defs>
            {/* Day-Ahead Market Gradient */}
            <linearGradient id="daGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00aaff" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#00aaff" stopOpacity={0.05} />
            </linearGradient>
            {/* Real-Time Market Gradient */}
            <linearGradient id="rtGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ff6b35" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ff6b35" stopOpacity={0.05} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="1 1" stroke="#333333" />

          <XAxis
            dataKey="time"
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
            width={45}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* Day-Ahead Market Area */}
          <Area
            type="monotone"
            dataKey="daPrice"
            stroke="#00aaff"
            strokeWidth={2}
            fill="url(#daGradient)"
            name="Day-Ahead"
          />

          {/* Real-Time Market Area */}
          <Area
            type="monotone"
            dataKey="rtPrice"
            stroke="#ff6b35"
            strokeWidth={2}
            fill="url(#rtGradient)"
            name="Real-Time"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Chart Legend */}
      <div className="chart-legend">
        <div className="legend-item">
          <div className="legend-color" style={{ background: '#00aaff' }} />
          Day-Ahead Market
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: '#ff6b35' }} />
          Real-Time Market
        </div>
      </div>

      {/* Timeline Brush Navigation */}
      {chartData.length > 10 && (
        <div style={{ marginTop: 16 }}>
          <ResponsiveContainer width="100%" height={40}>
            <AreaChart data={chartData}>
              <XAxis dataKey="time" hide />
              <YAxis hide />

              <Area
                type="monotone"
                dataKey="daPrice"
                stroke="#00aaff"
                strokeWidth={1}
                fill="#00aaff"
                fillOpacity={0.2}
              />

              <Brush
                dataKey="time"
                height={30}
                stroke="#00aaff"
                fill="#1a1a1a"
                onChange={handleBrushChange}
                startIndex={brushDomain?.[0] ?? 0}
                endIndex={brushDomain?.[1] ?? chartData.length - 1}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default EnhancedPriceChart;