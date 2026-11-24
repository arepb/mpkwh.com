# PRD: MPkWh “Which Gas Cars Pay for This EV?” Pages

**Product:** MPkWh.com  
**Feature:** EV break-even / “free car” calculator  
**Status:** Draft v1  
**Primary objective:** Turn MPkWh efficiency data into an actionable consumer decision tool showing when avoided gasoline spending can offset the cost of adding or switching to an EV.

---

## 1. Product Summary

MPkWh currently answers:

> **Which EVs are the most energy-efficient?**

This feature adds a second, more consumer-oriented question:

> **Which gasoline cars cost enough to fuel that replacing their miles with this EV can effectively cover the EV’s monthly payment?**

Each EV model page will calculate a live **break-even MPG** using:

- the EV’s MPkWh efficiency
- current gasoline prices
- current residential electricity prices
- monthly miles driven
- current lease/payment terms
- optional charging losses
- optional lease mileage overage

The feature should be available in two directions:

1. **EV-first:** “Which gas cars can pay for this EV?”
2. **Gas-car-first:** “What EV can my current gas car pay for?”

The initial implementation should focus on the EV-first experience, beginning with the Tesla Model 3, then expanding across the MPkWh database.

---

# 2. Why This Matters

Most EV savings calculators answer a generic question:

> “How much will I save on fuel?”

MPkWh can make the calculation more concrete:

> “Could the fuel savings from my current vehicle effectively pay for another car?”

This reframes EV efficiency from an abstract technical metric into a monthly household budget decision.

The feature also creates a natural internal-link destination for every vehicle on the MPkWh leaderboard and gives MPkWh a differentiated metric:

> **Break-even MPG**

This is the MPG threshold below which a gasoline vehicle spends enough on fuel to cover the EV’s monthly payment plus electricity.

---

# 3. Primary User Stories

## 3.1 EV-first user

As a consumer considering a specific EV, I want to know:

> “How inefficient does my current gas vehicle have to be for fuel savings to cover this EV?”

Example:

- EV: Tesla Model 3
- Lease: $299/month
- Miles: 1,000/month
- Gas: current Michigan price
- Electricity: current Michigan residential rate

Output:

> “At today’s energy prices, a gas vehicle getting approximately 12 MPG or less may spend enough on fuel for the savings to cover the advertised Model 3 lease payment.”

---

## 3.2 Gas-car-first user

As an owner of a truck or SUV, I want to know:

> “What EV could my current vehicle effectively pay for?”

Example:

- Current vehicle: Ford F-150
- MPG: 18
- Miles: 1,500/month
- Fuel: regular
- Location: Michigan

Output:

| EV | EV payment | Electricity | Avoided gas | Net monthly cost |
|---|---:|---:|---:|---:|
| Tesla Model 3 | $299 | $65 | $352 | +$12 |
| Tesla Model Y | $399 | $68 | $352 | +$115 |
| Nissan LEAF | $439 | $70 | $352 | +$157 |

---

# 4. Core Definition of “Free”

MPkWh should not claim that an EV literally has zero total ownership cost.

For this product:

> **“Fuel savings cover the payment” means avoided gasoline spending is equal to or greater than the EV’s monthly payment plus electricity cost.**

The calculation does **not** automatically include:

- insurance
- registration
- sales/use tax
- maintenance
- depreciation
- financing opportunity cost
- parking
- home charger installation

These can be disclosed clearly.

Suggested language:

> **Fuel savings cover the payment**

Alternative headline:

> **Which gas cars can make this EV effectively $0/month?**

Supporting disclaimer:

> Based on fuel and electricity costs only. Insurance, taxes, registration, maintenance and other ownership costs are not included.

---

# 5. Calculation Framework

## 5.1 Gasoline vehicle monthly fuel cost

```text
gas_monthly_cost =
    (monthly_miles / vehicle_mpg) * gas_price_per_gallon
```

Use the appropriate fuel grade where known:

- regular
- midgrade
- premium

If fuel-grade requirement is unknown, default to regular and label the assumption.

---

## 5.2 EV monthly electricity consumption

```text
ev_kwh_per_month =
    monthly_miles / ev_miles_per_kwh
```

---

## 5.3 EV charging overhead

MPkWh efficiency is primarily a vehicle-efficiency metric.

The consumer calculator should optionally account for charging losses.

Default:

```text
charging_overhead = 15%
```

Then:

```text
wall_kwh =
    ev_kwh_per_month * 1.15
```

This assumption should be visible and editable.

---

## 5.4 EV monthly electricity cost

```text
ev_electricity_cost =
    wall_kwh * electricity_price_per_kwh
```

---

## 5.5 Advertised-payment monthly cost

```text
ev_monthly_cost_advertised =
    advertised_monthly_payment
    + ev_electricity_cost
    + mileage_overage
```

---

## 5.6 Effective lease cost

A second mode should amortize mandatory upfront costs.

```text
effective_monthly_lease_cost =
    advertised_monthly_payment
    + (down_payment + acquisition_fee + other_required_fees) / lease_term_months
```

Then:

```text
ev_monthly_cost_effective =
    effective_monthly_lease_cost
    + ev_electricity_cost
    + mileage_overage
```

Taxes should be excluded unless a reliable location-specific calculation is available.

---

## 5.7 Mileage overage

If:

```text
annualized_miles > lease_allowance
```

Then:

```text
annual_excess_miles =
    annualized_miles - lease_allowance

monthly_overage_cost =
    annual_excess_miles * overage_fee_per_mile / 12
```

This should be included automatically whenever the user exceeds the lease mileage limit.

---

## 5.8 Break-even MPG

The key MPkWh-derived metric:

```text
break_even_mpg =
    monthly_miles * gas_price
    /
    ev_monthly_cost
```

Where `ev_monthly_cost` can be either:

- advertised payment basis
- effective lease basis

Example conceptually:

> If the Model 3 plus electricity costs $345/month and gasoline is $4.20/gallon at 1,000 miles/month:

```text
break_even_mpg =
    1000 * 4.20 / 345
    ≈ 12.2 MPG
```

Any gas vehicle below approximately 12.2 MPG has enough avoided fuel cost to cover the EV payment plus electricity.

---

# 6. EV Model Page

## Recommended URL Structure

Use one canonical page per model rather than one page per trim.

Examples:

```text
/mpkwh.com/tesla-model-3/
/mpkwh.com/lucid-air/
/mpkwh.com/nissan-leaf/
/mpkwh.com/toyota-bz/
```

Configuration is selected within the page.

Example:

```text
Tesla Model 3
[ Standard RWD | Premium RWD | Premium AWD ]
```

This avoids SEO cannibalization between near-identical trim pages.

---

# 7. Recommended Page Layout

## 7.1 Vehicle summary

Example:

> # Tesla Model 3
>
> **Which gas cars can pay for a Model 3?**
>
> 4.62 mi/kWh  
> 321-mile range  
> Current advertised lease: $299/month

Include a visible timestamp:

> Offer verified September 2026

---

## 7.2 Break-even hero

Large result:

> ## Break-even: 12.1 MPG regular / 15.5 MPG premium
>
> At your selected mileage and energy prices, vehicles below these thresholds may spend enough on gasoline for the savings to cover the advertised Model 3 payment plus electricity.

Show both fuel grades where applicable.

---

# 8. Interactive Inputs

Recommended controls:

### Location
- U.S. national average
- State selector
- ZIP code later if robust source is available

### Monthly miles
Default:

```text
1,000 miles/month
```

Suggested range:

```text
500–3,000 miles/month
```

Also show annual equivalent.

### Gasoline price
Auto-filled but editable.

### Premium gasoline price
Auto-filled but editable.

### Electricity price
Auto-filled but editable.

### Charging overhead
Default:

```text
15%
```

Editable:

```text
0–25%
```

### Payment basis

Toggle:

```text
[ Advertised payment ] [ Effective lease cost ]
```

### Lease offer
Auto-filled from current stored offer.

Allow manual override.

---

# 9. Example Comparison Table

Directly below the calculator:

> ## Cars that could pay for this EV

| Gas vehicle | Combined MPG | Fuel | Est. gas/month | EV/month | Difference |
|---|---:|---|---:|---:|---:|
| Ford F-150 Raptor R | 12 | Premium | $___ | $___ | Save $___ |
| Cadillac Escalade-V | 13 | Premium | $___ | $___ | Save $___ |
| Mercedes-AMG G63 | 15 | Premium | $___ | $___ | +$___ |
| Ford F-150 V8 4WD | 19 | Regular | $___ | $___ | +$___ |
| Ford Escape | 30 | Regular | $___ | $___ | +$___ |

The table should recalculate instantly when the user changes:

- mileage
- location
- gas price
- electricity price
- payment mode

---

# 10. Vehicle Matching Logic

The gas comparison database should come from official EPA vehicle data where possible.

Rank candidate gas vehicles by proximity to break-even.

Suggested groupings:

### Fuel savings more than cover EV
```text
net_difference <= 0
```

Label:

> **Fuel savings cover the payment**

### Near break-even
Within approximately:

```text
±$50/month
```

Label:

> **Nearly fuel-cost neutral**

### Does not cover EV
```text
net_difference > $50/month
```

Label:

> **Costs $X/month more**

---

# 11. Inverse Calculator

Recommended URL:

```text
/free-ev-calculator/
```

Potential headline:

> # What EV can your gas car pay for?

Workflow:

### Step 1
Select current gas vehicle.

```text
Year
Make
Model
Powertrain / trim
```

### Step 2
Enter monthly miles.

### Step 3
Select location.

### Step 4
Calculate avoided fuel spend.

### Step 5
Compare against all MPkWh EVs with active payment/lease data.

Output:

| EV | Payment | Electricity | Gas savings | Net monthly cost |
|---|---:|---:|---:|---:|
| Tesla Model 3 | $299 | $___ | $___ | **-$___** |
| Tesla Model Y | $___ | $___ | $___ | +$___ |
| Nissan LEAF | $___ | $___ | $___ | +$___ |
| Toyota bZ | $___ | $___ | $___ | +$___ |
| Lucid Air Pure | $699 | $___ | $___ | +$___ |

---

# 12. MPkWh Homepage Integration

Add a CTA from the existing leaderboard.

Potential labels:

```text
Break-even →
```

or:

```text
Can gas savings pay for it? →
```

Potential future sortable column:

```text
Break-even MPG
```

Example:

| EV | Mi/kWh | Cost / 100 mi | Break-even MPG |
|---|---:|---:|---:|
| Tesla Model 3 | 4.62 | $___ | 12.1 |
| Nissan LEAF | 4.27 | $___ | 8.7 |
| Lucid Air Pure | 5.00 | $___ | 5.7 |

Only show Break-even MPG when an active current lease/payment offer exists.

---

# 13. Data Sources

## 13.1 EV efficiency

Source:

```text
MPkWh internal dataset
```

Fields required:

```text
make
model
trim
model_year
miles_per_kwh
epa_range
usable_battery_kwh
```

Use existing MPkWh update process.

---

## 13.2 Gasoline prices

Preferred:

**U.S. Energy Information Administration (EIA)**

Data required:

```text
regular_price
midgrade_price
premium_price
region
state if available
last_updated
```

Recommended update frequency:

```text
Weekly
```

---

## 13.3 Residential electricity prices

Preferred:

**EIA**

Data required:

```text
residential_electricity_price
state
national_average
period
last_updated
```

Recommended update frequency:

```text
Monthly
```

Because electricity data may lag, always show:

> Latest available EIA residential rate

---

## 13.4 Gas vehicle MPG

Preferred:

**FuelEconomy.gov / EPA**

Fields required:

```text
year
make
model
trim/configuration
combined_mpg
city_mpg
highway_mpg
fuel_type
recommended_fuel_grade
vehicle_id
```

Recommended refresh:

```text
Monthly or when new model years appear
```

---

## 13.5 EV lease/payment offers

This is the least standardized data source and should be maintained separately.

Store:

```text
make
model
trim
monthly_payment
term_months
down_payment
acquisition_fee
other_required_upfront
annual_mileage_allowance
overage_fee_per_mile
offer_start_date
offer_end_date
source_url
verified_at
market_or_region
qualification_notes
```

Recommended refresh:

```text
Weekly
```

For launch, manual verification is acceptable.

---

# 14. Offer Freshness Rules

An offer should never appear without:

```text
verified_at
source_url
```

If:

```text
today - verified_at > 14 days
```

display:

> Offer may have changed. Verify current pricing.

If the offer expires:

- retain historic data internally
- remove from active break-even ranking
- allow user to manually input a payment

---

# 15. Important Lease Qualifications

Offers can vary based on:

- credit tier
- geography
- inventory
- trim
- loyalty
- conquest incentives
- first-time EV incentives
- taxes
- delivery fees

The UI should clearly distinguish:

```text
Advertised offer
```

from:

```text
Your actual payment
```

Users should be able to overwrite every payment field.

---

# 16. SEO Strategy

These pages have strong long-tail potential.

Examples:

```text
How much does a Tesla Model 3 save vs Ford F-150?
Can gas savings pay for a Tesla?
Tesla Model 3 break-even MPG
Tesla Model 3 vs Ford F-150 fuel cost
What car can I replace with a Tesla and save money?
Lucid Air fuel savings
EV fuel savings calculator
```

Recommended page title:

> Tesla Model 3 Fuel Savings & Break-Even MPG | MPkWh

Recommended H1:

> Which Gas Cars Can Pay for a Tesla Model 3?

Supporting copy should explain the methodology in plain English while exposing the calculation assumptions.

---

# 17. Structured Data / Indexability

Each canonical model page should be server-rendered or statically generated enough that search engines can see:

- EV name
- MPkWh
- current offer
- electricity cost
- default break-even MPG
- explanatory text
- example comparison vehicles

Do not make all meaningful content dependent on client-side JavaScript.

Calculator interaction can remain client-side.

---

# 18. Sharing

Generate shareable dynamic URLs when users modify assumptions.

Example:

```text
/tesla-model-3/?state=MI&miles=1200&basis=advertised
```

Potential share card:

> **At 1,200 miles/month, a 14-MPG premium-fuel vehicle could spend enough on gasoline to cover a Model 3 lease.**

This could become a useful social distribution mechanism.

---

# 19. Design Principles

The product should feel like a reference utility, not an auto-sales lead form.

Priorities:

1. Explain assumptions clearly.
2. Let users edit every important input.
3. Keep the main answer visible immediately.
4. Show calculations rather than hiding methodology.
5. Distinguish advertised pricing from effective pricing.
6. Include timestamps on dynamic inputs.
7. Avoid exaggerated “free car” claims without qualification.

---

# 20. Recommended Terminology

## Primary consumer phrase

> **Fuel savings cover the payment**

## Metric

> **Break-even MPG**

Definition:

> The gasoline MPG at which monthly gasoline spending equals the EV’s monthly payment plus electricity.

## Secondary marketing phrase

> **Which cars make this EV effectively $0/month?**

Always accompany this with:

> Fuel and electricity costs only.

---

# 21. MVP

## Phase 1 — Tesla Model 3 page

Build:

```text
/tesla-model-3/
```

Features:

- MPkWh trim selector
- current lease offer
- miles/month control
- state selector
- current gas/electricity prices
- advertised vs effective payment toggle
- break-even MPG
- regular/premium thresholds
- comparison table
- source timestamps
- editable assumptions

This page validates the product concept.

---

## Phase 2 — All MPkWh model pages

Build the same template for every EV on MPkWh.

Only show lease-derived break-even calculations when active offer data exists.

Otherwise:

> Enter your monthly payment

or use:

- financing calculator later
- purchase-price amortization later

---

## Phase 3 — Inverse calculator

Build:

```text
/free-ev-calculator/
```

User selects current gasoline vehicle.

MPkWh ranks available EVs by:

```text
net monthly incremental cost
```

Primary outcome:

> These EVs could be mostly or entirely paid for by your avoided gasoline spending.

---

# 22. Future Features

Potential later additions:

### Finance payment mode
Calculate monthly ownership based on:

- MSRP
- down payment
- APR
- loan term

### Purchase economics
Compare total cost over:

- 3 years
- 5 years
- 7 years

### Insurance delta
Optional user-entered insurance difference.

### Home charging
Allow:

- utility rate
- time-of-use rate
- off-peak rate
- solar marginal rate

### Public charging
Adjust electricity cost based on:

- home charging %
- public charging %
- DC fast charging rate

### Vehicle-specific premium-fuel rules
Automatically determine required vs recommended octane.

### Maintenance
Optional estimated maintenance savings.

### Depreciation
Potentially useful but should not be part of MVP because it introduces far more uncertainty.

---

# 23. Edge Cases

## Very low mileage

At low monthly mileage, avoided gas spending may be small.

Do not hide negative results.

Example:

> At 500 miles/month, fuel savings alone would not cover this EV payment.

---

## Very high mileage

If mileage exceeds a lease allowance:

- automatically calculate lease overage
- clearly show the penalty
- warn users that a purchase/finance option may be more appropriate

---

## Premium fuel

Use premium pricing where the comparison vehicle requires premium.

If premium is only recommended rather than required, provide an assumption indicator.

---

## Plug-in hybrids

Do not mix PHEVs into gasoline vehicle comparisons in MVP unless their actual electric/gas usage is modeled.

---

## Diesel

Support later as a separate fuel type with its own live fuel price.

---

## Missing current offer

If no active offer is stored:

> **No current lease offer tracked. Enter a monthly payment to calculate break-even.**

---

# 24. Analytics

Track:

```text
model_page_view
calculator_interaction
state_changed
miles_changed
payment_basis_changed
manual_price_override
gas_vehicle_clicked
inverse_calculator_started
inverse_calculator_completed
share_link_created
outbound_offer_click
```

Important product metric:

> Percentage of model-page visitors who interact with the break-even calculator.

---

# 25. Success Metrics

### Initial

- calculator engagement rate
- model-page dwell time
- return visits
- organic traffic to model pages
- internal click-through from MPkWh leaderboard

### Later

- inverse calculator completions
- shares
- search impressions for model-vs-model queries
- percentage of users finding at least one “fuel savings cover payment” result

---

# 26. Acceptance Criteria — Model Page

A model page is complete when:

- [ ] EV efficiency comes from the MPkWh database.
- [ ] User can select vehicle configuration.
- [ ] User can choose U.S. or state energy pricing.
- [ ] Gas price displays source and update date.
- [ ] Electricity price displays source and data period.
- [ ] Monthly mileage is editable.
- [ ] Charging overhead is included and editable.
- [ ] Current advertised lease offer is displayed.
- [ ] Offer source and verification date are displayed.
- [ ] Advertised and effective lease modes both work.
- [ ] Lease mileage overage is calculated automatically.
- [ ] Break-even MPG updates immediately.
- [ ] Regular and premium thresholds are supported.
- [ ] Gas comparison vehicles are ranked correctly.
- [ ] All assumptions can be manually overridden.
- [ ] “Free” claims include a fuel-cost-only qualification.
- [ ] Page has a canonical URL and indexable default state.

---

# 27. Recommended Launch Sequence

### 1.
Launch Tesla Model 3.

### 2.
Add:

- Tesla Model Y
- Nissan LEAF
- Toyota bZ
- Subaru Uncharted
- Lucid Air

These offer a useful range of:

- efficiency
- payment
- price point
- break-even thresholds

### 3.
Add the inverse calculator.

### 4.
Add “Break-even MPG” to the main MPkWh leaderboard for EVs with active offers.

---

# 28. Product Positioning

MPkWh begins as an efficiency reference:

> **How far does an EV travel on one kWh?**

This feature turns that same dataset into an economic reference:

> **How inefficient does your gas car need to be before the fuel savings can pay for an EV?**

That is the core product insight.

The feature should remain mathematically transparent, highly current and easy to verify — consistent with MPkWh as a durable reference utility rather than an automotive shopping lead-generation site.
