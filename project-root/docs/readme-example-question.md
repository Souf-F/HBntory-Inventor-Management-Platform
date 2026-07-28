docs/readme_example_questions.md
markdown
## Example questions

The public chat assistant answers 4 types of questions about the product catalog and branch stock. Below is one example of each, matching the suggestion chips shown in the chat interface.

### 1. Product details

Give me the details of product HB-MON-2102


### 2. Where a product is available

Where can I find the 24 inch Compact Monitor?


### 3. What products are available in one branch

What products are available at HBntory Paris?


### 4. Shopping list feasibility (multiple products with quantities)

I need 3 units of 8-Port Managed Switch and 2 of Barcode Scanner USB, which branch(es) can supply all of it?


Any question outside these 4 categories is politely declined by the assistant, which does not call any tool in that case. Branch names must match an existing branch exactly (`HBntory Paris`, `HBntory Lyon`, `HBntory Marseille`) — the assistant has no fuzzy matching and will say so if an unknown branch name is given.