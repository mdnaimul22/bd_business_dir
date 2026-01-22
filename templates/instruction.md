
**Role:** You are a Senior Software Architect and Product Designer with extensive experience in ERP systems, custom framework development, local directory systems, and tag-based search architecture.

**Context:**
I am developing a custom platform for an organization that serves multiple purposes. It functions partially as an ERP system while simultaneously operating as a public website and local shop directory. Users can search for shops and products using various keywords (e.g., "lathe," "spring," etc.).

**Existing Features:**
- Local shop directory system
- Product-based search functionality
- Tag system for products
- Support for multiple shops carrying multiple product types

**New Requirements:**

**1. Client/Buyer Company Management:**
This organization has multiple buyer companies that order various materials and products from them for manufacturing purposes. Each buyer company requires a comprehensive profile containing:
- Company name
- Company address
- Multiple contact persons (names)
- Mobile number(s) for each contact person

**2. Sales & Order Management:**
- Each buyer company will be associated with multiple sales transactions
- Each sale record must include:
  - Sale date
  - Product name
  - Product quantity
  - Unit price and total price
  - Product weight
- Each sale transaction must store vouchers/bills uploaded by the buyer, organized by serial number

**3. Inventory & Tagging Logic:**
- Raw materials or products purchased from shops in the shop directory need to be trackable
- These items should be taggable/linkable to specific production orders or final products
- This enables tracing which shops' materials were used in which orders
- Complete material traceability from purchase to final product

**Task:**
Based on these requirements, please provide:

1. **High-Level System Architecture:** Propose a comprehensive system architecture that addresses all functional requirements

2. **Database Design:** Provide database entities and relationships (explain as text-based ER Diagram with clear entity descriptions and relationship cardinalities)

3. **Tagging & Linking Mechanism:** Explain in detail how the tag system and order-to-inventory linking will function, including:
   - How materials are linked to production orders
   - How traceability is maintained throughout the supply chain
   - Query patterns for tracking material usage

4. **Scalability Considerations:** Recommend design patterns and architectural decisions that will facilitate future scaling, including:
   - Performance optimization strategies
   - Database indexing considerations
   - Potential microservices boundaries
   - Caching strategies
   - Any additional modular design approaches

---
