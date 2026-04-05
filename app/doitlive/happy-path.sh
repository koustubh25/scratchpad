#doitlive shell: /bin/zsh
#doitlive prompt: {user.cyan}@{hostname.green}:{dir.bold.magenta} $
#doitlive speed: 2
#doitlive commentecho: true

# Modernization demo happy path
pwd
ls

# Start from a clean state directory for the demo run
rm -rf .modernize

# Initialize the project against the sample ColdFusion app
python3 modernize.py init ../mock_tool/sample_app

# Choose the AI provider before semantic extraction
# In a live demo, pick openai / anthropic / gemini / command-json as appropriate.
python3 modernize.py choose-provider

# Discover source and config inputs
python3 modernize.py discover

# Parse source files into AST-like artifacts
python3 modernize.py parse

# Extract deterministic facts
python3 modernize.py facts

# Derive AI-assisted semantics
python3 modernize.py extract

# Review current semantic output
python3 modernize.py review semantics

# Demonstrate a human correction
python3 modernize.py correct semantics login --field summary --value "Login handles sign-in and delegates identity checks."

# Approve and lock semantics
python3 modernize.py approve semantics --all
python3 modernize.py lock semantics

# Derive, review, and lock source architecture
python3 modernize.py source-architect
python3 modernize.py review source-architecture
python3 modernize.py approve source-architecture
python3 modernize.py lock source-architecture

# Choose target stack only after source architecture is locked
python3 modernize.py choose-target-stack --target-stack python:backend,react:frontend --architecture-style microservice --deployment-style multi-deployable

# Derive, review, and lock target architecture
python3 modernize.py target-architect
python3 modernize.py review target-architecture
python3 modernize.py approve target-architecture
python3 modernize.py lock target-architecture

# Generate and verify the target application
python3 modernize.py generate demo-app
python3 modernize.py verify demo-app

# Show final pipeline and lock status
python3 modernize.py status
