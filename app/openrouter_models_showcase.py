"""
OpenRouter Models Showcase Data
Real OpenRouter models categorized for movieshaker.com use cases
All models are available through OpenRouter API
"""

OPENROUTER_SHOWCASE = {
    "script": {
        "title": "Script & Creative Writing",
        "icon": "📝",
        "description": "AI models for screenplays, dialogue, and story development",
        "models": [
            {
                "id": "anthropic/claude-3-opus",
                "name": "Claude 3 Opus",
                "provider": "Anthropic",
                "best_for": [
                    "Feature film screenplays",
                    "Complex character development",
                    "Long-form narrative"
                ],
                "strengths": [
                    "200K token context window",
                    "Exceptional creative writing",
                    "Nuanced dialogue generation",
                    "Industry format knowledge"
                ],
                "limitations": [
                    "Higher cost per request",
                    "Slower than Sonnet variants"
                ],
                "output_specs": "Up to 200,000 tokens (~150 pages)",
                "estimated_cost": "$0.015 per 1K tokens (input), $0.075 per 1K tokens (output)",
                "use_cases": [
                    "Full feature screenplays",
                    "Character arc development",
                    "Dialogue polishing",
                    "Story structure analysis"
                ]
            },
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "Anthropic",
                "best_for": [
                    "Fast screenplay drafts",
                    "Scene writing",
                    "Script editing"
                ],
                "strengths": [
                    "Excellent speed/quality balance",
                    "200K context window",
                    "Strong analytical abilities",
                    "Cost-effective"
                ],
                "limitations": [
                    "Less creative than Opus",
                    "Better for shorter pieces"
                ],
                "output_specs": "Up to 200,000 tokens",
                "estimated_cost": "$0.003 per 1K tokens (input), $0.015 per 1K tokens (output)",
                "use_cases": [
                    "Short film scripts",
                    "Commercial scripts",
                    "Scene rewrites",
                    "Script coverage notes"
                ]
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "best_for": [
                    "Quick scene generation",
                    "Brainstorming",
                    "Dialogue drafts"
                ],
                "strengths": [
                    "Very fast responses",
                    "128K context window",
                    "Versatile across genres",
                    "Good cost/performance ratio"
                ],
                "limitations": [
                    "Less nuanced than Claude for long-form",
                    "Smaller context than Claude"
                ],
                "output_specs": "Up to 128,000 tokens (~90 pages)",
                "estimated_cost": "$0.0025 per 1K tokens (input), $0.010 per 1K tokens (output)",
                "use_cases": [
                    "Beat sheets and outlines",
                    "Quick scene drafts",
                    "Character brainstorming",
                    "Genre-specific templates"
                ]
            },
            {
                "id": "openai/gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "provider": "OpenAI",
                "best_for": [
                    "Detailed scene work",
                    "Story structure",
                    "Treatment writing"
                ],
                "strengths": [
                    "128K context window",
                    "Strong reasoning",
                    "Good for complex plots",
                    "Reliable output"
                ],
                "limitations": [
                    "More expensive than GPT-4o",
                    "Slower than GPT-4o"
                ],
                "output_specs": "Up to 128,000 tokens",
                "estimated_cost": "$0.010 per 1K tokens (input), $0.030 per 1K tokens (output)",
                "use_cases": [
                    "Film treatments",
                    "Scene sequences",
                    "Plot development",
                    "Story bible creation"
                ]
            },
            {
                "id": "meta-llama/llama-3-70b-instruct",
                "name": "Llama 3 70B Instruct",
                "provider": "Meta",
                "best_for": [
                    "Budget-friendly drafts",
                    "High-volume content",
                    "Quick iterations"
                ],
                "strengths": [
                    "Very cost-effective",
                    "Fast generation",
                    "Open source model",
                    "Good for iterations"
                ],
                "limitations": [
                    "Less creative than Claude/GPT-4",
                    "8K context limit",
                    "May need more editing"
                ],
                "output_specs": "Up to 8,000 tokens",
                "estimated_cost": "$0.00059 per 1K tokens (input), $0.00079 per 1K tokens (output)",
                "use_cases": [
                    "First draft generation",
                    "Dialogue variations",
                    "Scene alternatives",
                    "Bulk content creation"
                ]
            }
        ]
    },
    "budget": {
        "title": "Budget & Financial Planning",
        "icon": "💰",
        "description": "AI models for budget analysis and financial planning",
        "models": [
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "Anthropic",
                "best_for": [
                    "Detailed budget breakdowns",
                    "Cost analysis",
                    "Financial modeling"
                ],
                "strengths": [
                    "Excellent with structured data",
                    "Accurate calculations",
                    "Can generate spreadsheet formats",
                    "Understands industry costs"
                ],
                "limitations": [
                    "Needs specific input data",
                    "May require verification"
                ],
                "output_specs": "Structured budget data, CSV/Excel ready",
                "estimated_cost": "$0.003 per 1K tokens (input), $0.015 per 1K tokens (output)",
                "use_cases": [
                    "Line-item budget creation",
                    "Department cost breakdowns",
                    "Budget optimization",
                    "Cost comparison analysis"
                ]
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "best_for": [
                    "Quick budget estimates",
                    "Cost projections",
                    "Financial summaries"
                ],
                "strengths": [
                    "Fast analysis",
                    "Good for initial planning",
                    "Flexible formatting",
                    "Cost-effective"
                ],
                "limitations": [
                    "Less detailed than Claude",
                    "Better with templates"
                ],
                "output_specs": "Budget estimates and breakdowns",
                "estimated_cost": "$0.0025 per 1K tokens (input), $0.010 per 1K tokens (output)",
                "use_cases": [
                    "Initial budget drafts",
                    "Quick cost estimates",
                    "Category planning",
                    "Savings recommendations"
                ]
            },
            {
                "id": "openai/gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "provider": "OpenAI",
                "best_for": [
                    "Complex financial analysis",
                    "Multi-project budgets",
                    "Detailed forecasting"
                ],
                "strengths": [
                    "Strong analytical abilities",
                    "Handles complex scenarios",
                    "Detailed breakdowns",
                    "Good with formulas"
                ],
                "limitations": [
                    "Higher cost",
                    "May be overkill for simple budgets"
                ],
                "output_specs": "Comprehensive financial documents",
                "estimated_cost": "$0.010 per 1K tokens (input), $0.030 per 1K tokens (output)",
                "use_cases": [
                    "Multi-film budget planning",
                    "Production company forecasts",
                    "Investment analysis",
                    "ROI calculations"
                ]
            }
        ]
    },
    "funding": {
        "title": "Funding & Pitch Development",
        "icon": "💼",
        "description": "AI models for investor pitches, grant proposals, and business plans",
        "models": [
            {
                "id": "anthropic/claude-3-opus",
                "name": "Claude 3 Opus",
                "provider": "Anthropic",
                "best_for": [
                    "Investor pitch decks",
                    "Grant proposals",
                    "Business plans"
                ],
                "strengths": [
                    "Highly persuasive writing",
                    "Understands business context",
                    "Professional tone",
                    "Detailed analysis"
                ],
                "limitations": [
                    "Higher cost",
                    "Requires detailed input"
                ],
                "output_specs": "Comprehensive business documents",
                "estimated_cost": "$0.015 per 1K tokens (input), $0.075 per 1K tokens (output)",
                "use_cases": [
                    "Full investor pitch decks",
                    "Grant applications",
                    "Crowdfunding campaigns",
                    "Partnership proposals"
                ]
            },
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "Anthropic",
                "best_for": [
                    "Business proposals",
                    "Sponsorship pitches",
                    "Executive summaries"
                ],
                "strengths": [
                    "Clear, professional writing",
                    "Fast generation",
                    "Cost-effective",
                    "Good structure"
                ],
                "limitations": [
                    "Less persuasive than Opus",
                    "Better for shorter docs"
                ],
                "output_specs": "Professional business documents",
                "estimated_cost": "$0.003 per 1K tokens (input), $0.015 per 1K tokens (output)",
                "use_cases": [
                    "Sponsorship proposals",
                    "Partnership decks",
                    "Executive summaries",
                    "One-pagers"
                ]
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "best_for": [
                    "Email pitches",
                    "Quick proposals",
                    "Social media campaigns"
                ],
                "strengths": [
                    "Concise writing",
                    "Fast generation",
                    "Versatile formats",
                    "Good for short-form"
                ],
                "limitations": [
                    "Less detailed than Claude",
                    "Better for brief content"
                ],
                "output_specs": "Short-form pitch materials",
                "estimated_cost": "$0.0025 per 1K tokens (input), $0.010 per 1K tokens (output)",
                "use_cases": [
                    "Email pitches to investors",
                    "Social media fundraising",
                    "Crowdfunding descriptions",
                    "Quick proposals"
                ]
            }
        ]
    },
    "marketing": {
        "title": "Marketing & Promotion",
        "icon": "🎨",
        "description": "AI models for marketing copy, press releases, and promotional content",
        "models": [
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "Anthropic",
                "best_for": [
                    "Marketing copy",
                    "Press releases",
                    "Film descriptions"
                ],
                "strengths": [
                    "Engaging writing style",
                    "Brand voice adaptation",
                    "SEO-friendly content",
                    "Fast generation"
                ],
                "limitations": [
                    "May need tone refinement",
                    "Better with style guides"
                ],
                "output_specs": "Marketing and promotional content",
                "estimated_cost": "$0.003 per 1K tokens (input), $0.015 per 1K tokens (output)",
                "use_cases": [
                    "Film synopses",
                    "Press releases",
                    "Marketing campaigns",
                    "Website copy"
                ]
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "best_for": [
                    "Social media content",
                    "Ad copy",
                    "Taglines"
                ],
                "strengths": [
                    "Punchy, concise writing",
                    "Good for short-form",
                    "Platform-specific content",
                    "Quick variations"
                ],
                "limitations": [
                    "Less detailed than Claude",
                    "Better for brief content"
                ],
                "output_specs": "Social and advertising content",
                "estimated_cost": "$0.0025 per 1K tokens (input), $0.010 per 1K tokens (output)",
                "use_cases": [
                    "Social media posts",
                    "Ad campaigns",
                    "Taglines and slogans",
                    "Email marketing"
                ]
            },
            {
                "id": "meta-llama/llama-3-70b-instruct",
                "name": "Llama 3 70B Instruct",
                "provider": "Meta",
                "best_for": [
                    "Bulk content generation",
                    "Multiple variations",
                    "A/B testing content"
                ],
                "strengths": [
                    "Very cost-effective",
                    "Fast bulk generation",
                    "Good for variations",
                    "High volume friendly"
                ],
                "limitations": [
                    "May need more editing",
                    "Less sophisticated tone",
                    "Better for straightforward copy"
                ],
                "output_specs": "High-volume marketing content",
                "estimated_cost": "$0.00059 per 1K tokens (input), $0.00079 per 1K tokens (output)",
                "use_cases": [
                    "Bulk social media posts",
                    "A/B test variations",
                    "Content calendars",
                    "Multiple platform copies"
                ]
            }
        ]
    }
}

# Flat list of categories
OPENROUTER_CATEGORIES = [
    {"id": "script", "name": "Script & Creative Writing", "icon": "📝"},
    {"id": "budget", "name": "Budget & Financial Planning", "icon": "💰"},
    {"id": "funding", "name": "Funding & Pitch Development", "icon": "💼"},
    {"id": "marketing", "name": "Marketing & Promotion", "icon": "🎨"}
]
