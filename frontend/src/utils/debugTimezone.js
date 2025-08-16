// Quick debug script to test timezone conversion
// Run this in browser console to verify times

const testTimeConversion = () => {
  // Example UTC timestamp from your order (5:35 AM UTC)
  const utcTimestamp = "2025-08-16T05:35:00Z"
  
  console.log("=== Timezone Conversion Debug ===")
  console.log("UTC timestamp from backend:", utcTimestamp)
  
  // Method 1: Direct parsing (WRONG - treats as local)
  const wrong = dayjs(utcTimestamp)
  console.log("❌ Wrong (dayjs direct):", wrong.format('YYYY-MM-DD HH:mm:ss'))
  
  // Method 2: Parse as UTC then convert to EDT (CORRECT)
  const utcTime = dayjs.utc(utcTimestamp)
  const edtTime = utcTime.tz('America/New_York')
  
  console.log("✅ UTC parsed:", utcTime.format('YYYY-MM-DD HH:mm:ss [UTC]'))
  console.log("✅ EDT converted:", edtTime.format('YYYY-MM-DD HH:mm:ss [EDT]'))
  console.log("✅ Display format:", edtTime.format('HH:mm'))
  
  // Show the difference
  console.log("\n=== Summary ===")
  console.log("Backend sends: 2025-08-16T05:35:00Z (5:35 AM UTC)")
  console.log("Should display: 01:35 EDT (1:35 AM Eastern)")
  console.log("Actual display:", edtTime.format('HH:mm [EDT]'))
}

// Run the test
testTimeConversion()
