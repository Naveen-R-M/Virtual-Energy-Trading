# Frontend RT Order Timezone Fix

## Problem
When users select Real-Time trading intervals in Eastern Time (EDT/EST), the frontend is sending them as UTC with the wrong offset. For example:
- User selects: **1:00 AM EDT**
- Frontend sends: `2025-08-16T01:00:00Z` (WRONG - this is 1 AM UTC)
- Should send: `2025-08-16T05:00:00Z` (CORRECT - this is 1 AM EDT in UTC)

## Solution

### 1. Install Required Dependencies
```bash
npm install dayjs
```

### 2. Use the Timezone Utility
The `timezone.ts` utility file has been created with all necessary functions.

### 3. Update Order Creation

When creating an RT order, convert the selected time properly:

```typescript
import { timezoneUtils } from '@/utils/timezone'

// Example: User selects "01:00" in the time picker (Eastern Time)
const selectedTime = "2025-08-16 01:00" // This is in EDT

// Convert to UTC for API
const orderData = {
  market: 'real-time',
  hour_start: timezoneUtils.localToUTC(selectedTime), // "2025-08-16T05:00:00Z"
  time_slot: timezoneUtils.alignToRTInterval(selectedTime), // Aligns to 5-min boundary
  node: 'PJM_RTO',
  side: 'buy',
  limit_price: 50,
  quantity_mwh: 5,
  order_type: 'LMT'
}

// Send to API
await endpoints.createOrder(orderData)
```

### 4. Display RT Intervals Correctly

When showing available RT intervals to users:

```typescript
// Get next 4 hours of available intervals
const intervals = timezoneUtils.getAvailableRTIntervals(4)

// Display in dropdown
intervals.forEach(interval => {
  console.log(interval.display) // "14:35-14:40"
  console.log(interval.startUTC) // Use this for API calls
})
```

### 5. Format Existing Orders for Display

When displaying orders from the API:

```typescript
// Order from API has UTC times
const order = {
  time_slot: "2025-08-16T05:00:00Z" // 1:00 AM EDT in UTC
}

// Format for display
const displayTime = timezoneUtils.formatInterval(order.time_slot)
// Returns: "01:00-01:05 EDT"
```

## Key Functions

### `localToUTC(localTime)`
Converts Eastern Time to UTC for API calls
- Input: `"2025-08-16 01:00"` (EDT)
- Output: `"2025-08-16T05:00:00Z"` (UTC)

### `utcToLocal(utcTime)`
Converts UTC to Eastern Time for display
- Input: `"2025-08-16T05:00:00Z"`
- Output: Dayjs object in EDT

### `alignToRTInterval(time)`
Aligns any time to the nearest 5-minute boundary
- Input: `"2025-08-16 01:03"` 
- Output: `"2025-08-16T05:00:00Z"` (aligned to 01:00 EDT)

### `getCurrentRTInterval()`
Gets the current 5-minute interval
- Returns both UTC and local times

### `getAvailableRTIntervals(hours)`
Gets all available RT intervals for the next N hours
- Returns array with display strings and UTC times

## Testing

Test the conversion:
```typescript
// Should output "2025-08-16T05:00:00Z"
console.log(timezoneUtils.localToUTC("2025-08-16 01:00"))

// Should output "01:00-01:05 EDT"
console.log(timezoneUtils.formatInterval("2025-08-16T05:00:00Z"))
```

## Common Mistakes to Avoid

❌ **DON'T** send Eastern Time as if it were UTC:
```typescript
// WRONG
time_slot: "2025-08-16T01:00:00Z" // This means 1 AM UTC, not EDT!
```

✅ **DO** convert Eastern Time to UTC:
```typescript
// CORRECT
time_slot: timezoneUtils.localToUTC("2025-08-16 01:00") // "2025-08-16T05:00:00Z"
```

❌ **DON'T** display UTC times directly to users:
```typescript
// WRONG
<span>{order.time_slot}</span> // Shows "2025-08-16T05:00:00Z"
```

✅ **DO** format UTC times for Eastern timezone display:
```typescript
// CORRECT
<span>{timezoneUtils.formatInterval(order.time_slot)}</span> // Shows "01:00-01:05 EDT"
```
