# Roadmap

## 0.4.0
Features:
- Google Pass / PDF pass sending
- [x] Transactions: email check and sending confirmation popup
Bugfix:
- [ ] Transactions: select2 does not get rendered on new rows
- [x] Transactions: Return to list after receipt sending
- [ ] Transactions: Display/Translate Payment method values
Housekeeping:
- Own instance: resize all imported data first_name and last_name to Capital letters

## 0.4.1
Features:
- Transactions: Confirmation modal before saving
- Transactions: Confirmation modal before sending receipt
- Associates: Confirmation modal before sending membership card
Bugfixes:
- Transaction: search stopped working (Associates does)

# TODOs
## Refactoring
- Util functions all in one place
- Function naming consistency
- select2 being style consistant

## Subscriptions
- Have file upload more decent UI

## Associates
- Message when form Save is failing due to to field errors

## Transactions
- Membership minor fee should be added if a minor is included in a TransactionLine
- Find a better way to filter Membership Card article in signals.py
- Add email send confirmation (reporting email address)
- BUG: New rows do not get proper select2 element

# Bugfixes
## Associates
- /register test date picker behavior on mobile (no issues on Android FF/Chromium, iOS only?)
- Correct birth dates with years starting with 2xxx

## Subscriptions
- Do not show full attachment filename, it breaks layout. Just put a placeholder text

## Articles
- Add Counsellors discounted articles

## Feature brain dump
- Skipass warehouse management (people who paid multiple passes in advance)
- Reports (skipass list, social competition list)
- Article management (with pricing and custom rule set, e.g. Same article attached to a minor would have a different price)
- How to add skipass to report (from either transaction list or the skipass warehouse)
- Configuration management (e.g. Title, background image)

