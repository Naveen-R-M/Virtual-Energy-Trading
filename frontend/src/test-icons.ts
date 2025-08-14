// Test file to verify available Arco Design icons
import * as Icons from '@arco-design/web-react/icon'

console.log('Available Arco Design Icons:')
console.log(Object.keys(Icons).filter(name => name.startsWith('Icon')).sort())

// Test the specific icons we're using
const testIcons = [
  'IconArrowUp',
  'IconArrowDown', 
  'IconDollar',
  'IconTrophy',
  'IconCalendar',
  'IconRefresh',
  'IconLineChart',
  'IconTarget',
  'IconBarChart',
  'IconActivity',
  'IconTrendingUp'
]

console.log('Testing our icons:')
testIcons.forEach(iconName => {
  if (Icons[iconName as keyof typeof Icons]) {
    console.log(`✅ ${iconName} - Available`)
  } else {
    console.log(`❌ ${iconName} - NOT FOUND`)
  }
})

export {}
