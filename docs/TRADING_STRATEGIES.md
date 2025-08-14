# Virtual Energy Trading - Three common trading strategies

## 1️⃣ Day-Ahead (DA) → Real-Time (RT) Spread Trading

### **Idea**
- Buy or sell electricity **one day ahead** at a fixed price.
- When delivery happens, the market actually trades every **5 minutes** in the Real-Time (RT) market.
- Your profit/loss is the difference between your DA price and the average RT price.

### **Example**
- **DA Buy:** 10 MWh at **$50/MWh**
- **RT Prices:** Average over that hour = **$55/MWh**
- **Profit:**  
  ```
  Profit = (RT Avg Price − DA Price) × Quantity
         = (55 − 50) × 10
         = 5 × 10
         = $50
  ```
- If RT Avg was $48, the same trade would lose:  
  ```
  Loss = (48 − 50) × 10
       = (−2) × 10
       = −$20
  ```

✅ **Good for:** Taking a view on where prices will move between DA and RT.  
❌ **Risk:** If prices move against you, you lose.

---

## 2️⃣ Pure Real-Time (RT) Scalping

### **Idea**
- Skip DA entirely.
- Trade directly in the RT market, trying to buy low and sell high within minutes.

### **Example**
- **Buy:** 5 MWh at $40 (12:05 PM)
- **Sell:** 5 MWh at $42 (12:10 PM)
- **Profit:**  
  ```
  Profit = (Sell Price − Buy Price) × Quantity
         = (42 − 40) × 5
         = 2 × 5
         = $10
  ```

✅ **Good for:** Fast-paced trading.  
❌ **Risk:** Prices can change quickly; a sudden drop can cause losses.

---

## 3️⃣ Day-Ahead Hour Spread (DA Arbitrage)

### **Idea**
- Buy in one DA hour and sell in another DA hour.
- You’re betting that the **price difference (spread)** between the two hours in DA is different from the spread in RT.

### **Example**
- **DA Buy Hour 3:** $25/MWh  
- **DA Sell Hour 18:** $70/MWh  
- **Quantity:** 4 MWh

**DA Spread:**  
```
DA Spread = Sell Price − Buy Price
          = 70 − 25
          = 45
```

**RT Average Prices:**  
- Hour 3: $28  
- Hour 18: $66

**RT Spread:**  
```
RT Spread = 66 − 28
          = 38
```

**Profit:**  
```
Profit = (DA Spread − RT Spread) × Quantity
       = (45 − 38) × 4
       = 7 × 4
       = $28
```

✅ **Good for:** Taking a view on how hourly spreads will change between DA and RT.  
❌ **Risk:** If RT spread moves opposite to your DA bet, you lose.

---

## Summary Table

| Strategy                | How It Works                              | Profit Formula                                             | Example Profit |
|-------------------------|-------------------------------------------|------------------------------------------------------------|----------------|
| **DA → RT Spread**      | Buy/Sell in DA, close in RT                | `(RT Avg − DA Price) × Qty`                                | $50            |
| **RT Scalping**         | Buy low, sell high in RT                   | `(Sell Price − Buy Price) × Qty`                           | $10            |
| **DA Hour Spread**      | Buy one DA hour, sell another, compare RT  | `(DA Spread − RT Spread) × Qty`                            | $28            |

---

## Key Takeaways
- **DA → RT Spread**: You lock a price a day ahead and hope RT moves your way.  
- **RT Scalping**: Fast in-and-out trades in real time.  
- **DA Hour Spread**: Bet on changes in price differences between hours.

In all cases:  
**Profit if you buy low and sell high. Loss if you buy high and sell low.**