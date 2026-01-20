"""
MovieShaker AI Models Showcase Data
Categorized AI models for film and music production
"""

MOVIESHAKER_MODELS = {
    "music": {
        "title": "Music Generation",
        "icon": "🎵",
        "description": "AI models for creating songs, soundtracks, and audio",
        "models": [
            {
                "id": "suno/v3.5",
                "name": "Suno AI v3.5",
                "provider": "Suno",
                "best_for": [
                    "Full songs with vocals",
                    "Movie soundtracks",
                    "Theme music"
                ],
                "strengths": [
                    "High quality audio output",
                    "All music genres supported",
                    "Lyrics generation included",
                    "Professional mixing"
                ],
                "limitations": [
                    "4 minute maximum length",
                    "No separate stems export"
                ],
                "output_specs": "Up to 4 minutes, stereo MP3/WAV",
                "estimated_cost": "$0.05 per generation",
                "use_cases": [
                    "Opening/closing theme songs",
                    "Trailer background music",
                    "Scene-specific mood music"
                ]
            },
            {
                "id": "meta/musicgen",
                "name": "MusicGen",
                "provider": "Meta",
                "best_for": [
                    "Background music",
                    "Short loops (up to 30 seconds)",
                    "Ambient soundscapes"
                ],
                "strengths": [
                    "Fast generation",
                    "Good for electronic/ambient",
                    "Controllable with text prompts",
                    "Open source model"
                ],
                "limitations": [
                    "30 second maximum",
                    "Limited vocal support",
                    "Best for instrumental"
                ],
                "output_specs": "Up to 30 seconds, stereo WAV",
                "estimated_cost": "$0.02 per generation",
                "use_cases": [
                    "Background ambience",
                    "Transition music",
                    "Short musical stings"
                ]
            },
            {
                "id": "stable-audio/v1",
                "name": "Stable Audio",
                "provider": "Stability AI",
                "best_for": [
                    "Sound effects",
                    "Instrumental music",
                    "Audio textures"
                ],
                "strengths": [
                    "Precise control with prompts",
                    "Good for sound design",
                    "Variable length output",
                    "High fidelity"
                ],
                "limitations": [
                    "No vocal generation",
                    "Complex prompts needed"
                ],
                "output_specs": "Variable length, 44.1kHz stereo",
                "estimated_cost": "$0.03 per generation",
                "use_cases": [
                    "Sound effects for scenes",
                    "Atmospheric backgrounds",
                    "Musical transitions"
                ]
            }
        ]
    },
    "script": {
        "title": "Script Writing",
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
                    "Story editing and feedback"
                ],
                "strengths": [
                    "200K token context window",
                    "Excellent creative writing",
                    "Understands industry formatting",
                    "Nuanced dialogue generation"
                ],
                "limitations": [
                    "Higher cost per use",
                    "May need guidance on genre conventions"
                ],
                "output_specs": "Up to 200,000 tokens (~150 pages)",
                "estimated_cost": "$0.15 per full script",
                "use_cases": [
                    "Full screenplay generation",
                    "Scene breakdowns and outlines",
                    "Character arc development",
                    "Dialogue polishing and rewrites"
                ]
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "best_for": [
                    "Script brainstorming",
                    "Quick scene writing",
                    "Dialogue generation"
                ],
                "strengths": [
                    "Fast response time",
                    "Good for short scenes",
                    "Versatile across genres",
                    "Balanced cost/quality"
                ],
                "limitations": [
                    "128K token limit",
                    "Less nuanced than Claude for long-form"
                ],
                "output_specs": "Up to 128,000 tokens (~90 pages)",
                "estimated_cost": "$0.08 per script",
                "use_cases": [
                    "Quick scene drafts",
                    "Dialogue rewrites",
                    "Story concept exploration",
                    "Beat sheets"
                ]
            },
            {
                "id": "anthropic/claude-3-sonnet",
                "name": "Claude 3 Sonnet",
                "provider": "Anthropic",
                "best_for": [
                    "Short films and commercials",
                    "Script analysis",
                    "Character dialogue"
                ],
                "strengths": [
                    "Good balance of cost and quality",
                    "Fast generation",
                    "Strong dialogue skills",
                    "200K context"
                ],
                "limitations": [
                    "Not as creative as Opus",
                    "Better for shorter works"
                ],
                "output_specs": "Up to 200,000 tokens",
                "estimated_cost": "$0.05 per script",
                "use_cases": [
                    "Short film scripts",
                    "Commercial copy",
                    "Script coverage notes",
                    "Dialogue punch-up"
                ]
            }
        ]
    },
    "video": {
        "title": "Video Generation",
        "icon": "🎬",
        "description": "AI models for creating video content and animations",
        "models": [
            {
                "id": "runway/gen-2",
                "name": "Runway Gen-2",
                "provider": "Runway",
                "best_for": [
                    "Short video clips",
                    "Concept visualization",
                    "B-roll generation"
                ],
                "strengths": [
                    "Text and image to video",
                    "Realistic motion",
                    "Good for previsualization",
                    "Multiple aspect ratios"
                ],
                "limitations": [
                    "4 second maximum",
                    "Can have artifacts",
                    "Expensive per second"
                ],
                "output_specs": "Up to 4 seconds, 1080p",
                "estimated_cost": "$0.10 per second",
                "use_cases": [
                    "Storyboard visualization",
                    "Concept pitches",
                    "Visual effects previews",
                    "B-roll footage"
                ]
            },
            {
                "id": "pika/v1",
                "name": "Pika 1.0",
                "provider": "Pika Labs",
                "best_for": [
                    "Animated clips",
                    "Creative transitions",
                    "Stylized videos"
                ],
                "strengths": [
                    "Creative animation styles",
                    "Good motion control",
                    "Supports various formats",
                    "Camera movement control"
                ],
                "limitations": [
                    "3 second clips",
                    "Stylized look",
                    "Less photorealistic"
                ],
                "output_specs": "Up to 3 seconds, HD",
                "estimated_cost": "$0.08 per second",
                "use_cases": [
                    "Animated sequences",
                    "Creative transitions",
                    "Music video elements",
                    "Experimental footage"
                ]
            }
        ]
    },
    "budget": {
        "title": "Budget Planning",
        "icon": "💰",
        "description": "AI models for budget analysis and financial planning",
        "models": [
            {
                "id": "anthropic/claude-3-sonnet",
                "name": "Claude 3 Sonnet",
                "provider": "Anthropic",
                "best_for": [
                    "Budget breakdowns",
                    "Cost analysis",
                    "Resource planning"
                ],
                "strengths": [
                    "Excellent with structured data",
                    "Can generate detailed breakdowns",
                    "Understands film production costs",
                    "Good at calculations"
                ],
                "limitations": [
                    "Needs industry-specific data",
                    "May need verification"
                ],
                "output_specs": "Detailed spreadsheet-ready data",
                "estimated_cost": "$0.03 per budget",
                "use_cases": [
                    "Line-item budget creation",
                    "Cost comparison analysis",
                    "Budget optimization suggestions",
                    "Department cost breakdowns"
                ]
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "best_for": [
                    "Quick budget estimates",
                    "Budget category suggestions",
                    "Cost saving ideas"
                ],
                "strengths": [
                    "Fast analysis",
                    "Good for initial planning",
                    "Flexible formatting",
                    "Cost-effective"
                ],
                "limitations": [
                    "Less detailed than Claude",
                    "May need templates"
                ],
                "output_specs": "Structured budget data",
                "estimated_cost": "$0.02 per budget",
                "use_cases": [
                    "Initial budget drafts",
                    "Quick cost estimates",
                    "Budget category planning",
                    "Savings recommendations"
                ]
            }
        ]
    },
    "funding": {
        "title": "Funding & Pitches",
        "icon": "💼",
        "description": "AI models for pitch decks, investor materials, and funding proposals",
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
                    "Persuasive writing",
                    "Understands business context",
                    "Detailed analysis",
                    "Professional tone"
                ],
                "limitations": [
                    "Higher cost",
                    "Needs project details"
                ],
                "output_specs": "Comprehensive documents",
                "estimated_cost": "$0.12 per pitch deck",
                "use_cases": [
                    "Investor pitch decks",
                    "Grant applications",
                    "Crowdfunding campaigns",
                    "Sponsorship proposals"
                ]
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "best_for": [
                    "One-pagers",
                    "Email pitches",
                    "Quick proposals"
                ],
                "strengths": [
                    "Concise writing",
                    "Fast generation",
                    "Good for short formats",
                    "Versatile"
                ],
                "limitations": [
                    "Less detailed than Claude",
                    "Better for shorter content"
                ],
                "output_specs": "Short-form pitch materials",
                "estimated_cost": "$0.05 per pitch",
                "use_cases": [
                    "Email pitches to investors",
                    "One-page proposals",
                    "Crowdfunding descriptions",
                    "Social media campaigns"
                ]
            }
        ]
    }
}

# Flat list of all categories for easy access
CATEGORIES = [
    {"id": "music", "name": "Music Generation", "icon": "🎵"},
    {"id": "script", "name": "Script Writing", "icon": "📝"},
    {"id": "video", "name": "Video Generation", "icon": "🎬"},
    {"id": "budget", "name": "Budget Planning", "icon": "💰"},
    {"id": "funding", "name": "Funding & Pitches", "icon": "💼"}
]
