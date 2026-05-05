# Presenter Script

Target length: 6 minutes  
Stretch length: 7 to 8 minutes with pauses and light elaboration

## Slide 0
**Agentic Commerce using Universal Commerce Protocol**

"What I want to show today is a practical view of agentic commerce, and specifically how merchants can participate in it without giving up control of the transaction layer.

The core idea is simple: if agents become the new front door for commerce, merchants need a standard way to expose catalog, cart, checkout, and post-purchase capabilities to those agents.

That is where Universal Commerce Protocol, or UCP, comes in."

## Slide 1
**The Interface For Commerce Is Changing**

"For most of ecommerce, discovery started on the merchant’s own surface.

The customer came to the website, searched, browsed, filtered, and worked through the journey there.

What is changing now is not the underlying customer need, but the entry point.

Increasingly, discovery can begin in an agent interface instead of on the merchant website.

That means the merchant is no longer guaranteed to control the first interaction."

## Slide 2
**Traditional E-commerce vs Agent Guided Commerce**

"This slide shows the operational difference.

On the left is traditional ecommerce. The customer does the work: search, filters, browsing, comparison, and final choice.

On the right is agent-guided commerce. The customer expresses intent in natural language, the agent interprets it semantically, narrows the choice set, and helps guide the decision.

The key point is not magic.

The key point is that more of the searching, filtering, and comparison work shifts from the user to the agent."

## Slide 3
**When The Interface Moves, Value Can Move With It**

"This matters because when the interface moves, value can move with it.

If the customer interaction starts in the agent layer, then important merchant control points become more contested.

That includes traffic, brand visibility, ranking, customer data, and loyalty.

So the issue is not just a better interface.

It is a shift in who controls discovery, influence, and eventually monetisation."

## Slide 4
**A Standard Interface For Agentic Commerce**

"So the question becomes: how does a merchant participate in that world without building a bespoke integration for every new agent surface?

The answer is a standard interface layer.

On the left you have different agent surfaces.

On the right you have merchant capabilities like catalog, cart, checkout, identity linking, and orders.

UCP sits in the middle as the common protocol surface between those two sides."

## Slide 5
**Universal Commerce Protocol**

"UCP is not just an idea. It is a real protocol model and it is already live.

At a high level, UCP is an open standard for commerce interoperability. It gives platforms, agents, and businesses a common way to discover capabilities and transact without bespoke integrations.

Businesses publish a UCP profile at `/.well-known/ucp`.

Platforms advertise their own profile on requests.

Then the two sides negotiate compatible services, capabilities, and transports.

And importantly, this is already visible in the market. We have live verified merchant profiles from Australian merchants including JB Hi-Fi, Culture Kings, and Billy J."

## Slide 6
**Demo Setup**

"Now I’ll show how we applied that in the demo stack.

On the experience side, we have OlivePwC and UCP Playground as the demo surfaces. They are replaceable.

Below the merchant-owned boundary sits the merchant-owned UCP stack.

That includes the UCP merchant server and the commerce lifecycle capabilities behind it.

In this demo, identity and payments are mocked, but the rest of the interaction model is real.

For search and retrieval, the stack uses Vertex AI Search for Commerce.

We also use mealsDB as an external recipe lookup service.

For the demo, ingestion is based on manually scraped retail site reference data.

The broader point is that the same UCP stack can be reused beyond grocery. You change the source system and ingestion path, but the core pattern can extend into other verticals like travel and insurance."

## Slide 7
**What This Demo Proves**

"So what does the demo actually prove?

First, it proves the commerce flow itself: intent-led discovery, recipe-led basket building, loyalty-aware pricing, and the cart-to-checkout-to-order lifecycle through UCP.

Second, it proves interoperability. The same merchant server can support multiple agent surfaces, in our case both OlivePwC and UCP Playground.

Third, it proves merchant control. The merchant still owns the transaction layer, including the checkout handoff.

And strategically, that means the agent surface can change while the merchant-owned commerce stack remains stable.

That is the reason this matters.

It gives merchants a path into agentic commerce that is structured, reusable, and extensible rather than one-off and bespoke."

## Optional close

"The big question is not whether agents will participate in commerce.

The question is whether merchants will stay directly connected to that future, or whether they will be abstracted behind someone else’s interface.

Our view is that UCP is one practical way to keep merchants in the loop."
