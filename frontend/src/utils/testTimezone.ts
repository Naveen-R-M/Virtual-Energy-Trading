import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

// Configure dayjs
dayjs.extend(utc)
dayjs.extend(timezone)

// Test timezone conversion
function testTimeConversion() {
  console.log('=== TIMEZONE CONVERSION TEST ===\n')
  
  const testDate = '2025-08-16'
  const testCases = [
    { edtTime: '01:05', description: '1:05 AM EDT' },
    { edtTime: '12:00', description: '12:00 PM (Noon) EDT' },
    { edtTime: '20:45', description: '8:45 PM EDT' },
    { edtTime: '23:55', description: '11:55 PM EDT' }
  ]
  
  testCases.forEach(test => {
    const edtDateTime = dayjs.tz(`${testDate} ${test.edtTime}`, 'America/New_York')
    const utcDateTime = edtDateTime.utc()
    
    console.log(`${test.description}:`)
    console.log(`  EDT: ${edtDateTime.format('YYYY-MM-DD HH:mm:ss')} (User selects this)`)
    console.log(`  UTC: ${utcDateTime.format('YYYY-MM-DD HH:mm:ss')} (Send to API)`)
    console.log(`  API Format: ${utcDateTime.format()}`)
    console.log('')
  })
  
  // Show current time
  const now = dayjs()
  const nowEDT = now.tz('America/New_York')
  console.log('Current Time:')
  console.log(`  EDT: ${nowEDT.format('YYYY-MM-DD HH:mm:ss z')}`)
  console.log(`  UTC: ${now.utc().format('YYYY-MM-DD HH:mm:ss')}`)
}

// Run the test
testTimeConversion()

export default testTimeConversion
