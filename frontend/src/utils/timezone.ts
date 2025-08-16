import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

// Configure dayjs with timezone support
dayjs.extend(utc)
dayjs.extend(timezone)

// PJM operates in Eastern Time (America/New_York)
const MARKET_TIMEZONE = 'America/New_York'

/**
 * Convert a local EDT/EST time to UTC for API submission
 * @param dateStr - Date in YYYY-MM-DD format
 * @param timeStr - Time in HH:mm format (e.g., "01:05" for 1:05 AM EDT)
 * @returns ISO string in UTC (e.g., "2025-08-16T05:05:00Z")
 */
export function edtToUtc(dateStr: string, timeStr: string): string {
  // Parse the date and time in Eastern timezone
  const edtDateTime = dayjs.tz(`${dateStr} ${timeStr}`, MARKET_TIMEZONE)
  
  // Convert to UTC and return ISO string
  return edtDateTime.utc().format()
}

/**
 * Convert a UTC timestamp to local EDT/EST for display
 * @param utcTimestamp - UTC timestamp (e.g., "2025-08-16T05:05:00Z")
 * @returns Object with formatted date and time in Eastern timezone
 */
export function utcToEdt(utcTimestamp: string): {
  date: string
  time: string
  datetime: string
} {
  const edtTime = dayjs(utcTimestamp).tz(MARKET_TIMEZONE)
  
  return {
    date: edtTime.format('YYYY-MM-DD'),
    time: edtTime.format('HH:mm'),
    datetime: edtTime.format('YYYY-MM-DD HH:mm')
  }
}

/**
 * Get current time in Eastern timezone
 * @returns Current time in EDT/EST
 */
export function getCurrentEasternTime(): dayjs.Dayjs {
  return dayjs().tz(MARKET_TIMEZONE)
}

/**
 * Check if a given EDT/EST time has passed
 * @param dateStr - Date in YYYY-MM-DD format
 * @param timeStr - Time in HH:mm format
 * @returns true if the time has passed
 */
export function hasEdtTimePassed(dateStr: string, timeStr: string): boolean {
  const edtTime = dayjs.tz(`${dateStr} ${timeStr}`, MARKET_TIMEZONE)
  const now = dayjs().tz(MARKET_TIMEZONE)
  return edtTime.isBefore(now)
}

/**
 * Format time slot for RT market (5-minute intervals)
 * @param dateStr - Date in YYYY-MM-DD format
 * @param startTime - Start time in HH:mm format (e.g., "01:05")
 * @returns Object with UTC timestamps for the interval
 */
export function formatRTTimeSlot(dateStr: string, startTime: string): {
  hourStartUtc: string
  timeSlotUtc: string
  intervalEndUtc: string
} {
  // Parse start time in Eastern timezone
  const edtStart = dayjs.tz(`${dateStr} ${startTime}`, MARKET_TIMEZONE)
  
  // Calculate end of 5-minute interval
  const edtEnd = edtStart.add(5, 'minute')
  
  return {
    hourStartUtc: edtStart.utc().format(),
    timeSlotUtc: edtStart.utc().format(),
    intervalEndUtc: edtEnd.utc().format()
  }
}

/**
 * Format time for DA market (hourly)
 * @param dateStr - Date in YYYY-MM-DD format
 * @param hour - Hour in HH:00 format (e.g., "14:00")
 * @returns UTC timestamp for the hour
 */
export function formatDAHour(dateStr: string, hour: string): string {
  // Parse hour in Eastern timezone
  const edtHour = dayjs.tz(`${dateStr} ${hour}`, MARKET_TIMEZONE)
  
  // Convert to UTC
  return edtHour.utc().format()
}

/**
 * Debug helper: Show what a time means in both timezones
 * @param dateStr - Date in YYYY-MM-DD format
 * @param timeStr - Time in HH:mm format
 */
export function debugTimeConversion(dateStr: string, timeStr: string): {
  edt: string
  utc: string
  isFuture: boolean
} {
  const edtTime = dayjs.tz(`${dateStr} ${timeStr}`, MARKET_TIMEZONE)
  const utcTime = edtTime.utc()
  const now = dayjs()
  
  return {
    edt: edtTime.format('YYYY-MM-DD HH:mm:ss z'),
    utc: utcTime.format('YYYY-MM-DD HH:mm:ss [UTC]'),
    isFuture: edtTime.isAfter(now)
  }
}

export const timezoneUtils = {
  edtToUtc,
  utcToEdt,
  getCurrentEasternTime,
  hasEdtTimePassed,
  formatRTTimeSlot,
  formatDAHour,
  debugTimeConversion
}

export default timezoneUtils
