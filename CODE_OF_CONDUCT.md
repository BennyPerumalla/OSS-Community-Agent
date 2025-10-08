# Code of Conduct - OSS Community Agent

##  Our Pledge

As contributors, maintainers, and participants in the *OSS Community Agent* project, we pledge to make participation in our community a welcoming, inclusive, and harassment-free experience for everyone—regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, caste, color, religion, or sexual identity and orientation.

*Our mission* is to help open-source maintainers reclaim their time and reduce burnout by building a safe, controllable AI agent. We recognize the toll that repetitive community support takes on maintainers, and we're committed to fostering a community that values:

- *Empathy for maintainer time* – Understanding that this project exists to protect maintainers from burnout
- *Responsible AI development* – Building technology that is safe, transparent, and human-controlled
- *Collaborative innovation* – Working together to create tools that benefit the entire open-source ecosystem
- *Clear, constructive communication* – Given our project's focus on automated responses, we prioritize precise, helpful interactions

We are committed to acting and interacting in ways that contribute to an open, welcoming, diverse, inclusive, and healthy community.

---

##  Standards of Behavior

### Expected Behavior

We expect all community members to:

#### General Conduct
- *Be respectful and considerate* in all interactions, whether on GitHub, Reddit, Discord, Slack, or other platforms
- *Use welcoming and inclusive language* that makes all participants feel valued
- *Gracefully accept constructive criticism* and focus on what is best for the community and the project
- *Show empathy towards other community members* and assume good intent in communications
- *Focus on collaboration over competition* – we're all working toward the same goal

#### Project-Specific Conduct

*For Code Contributors:*
- Write clear, well-documented code that others can understand and maintain, especially given our planned integrations (ChromaDB/Milvus, Discord/Slack)
- Follow the existing code structure and patterns found in the repository
- Test your changes thoroughly, particularly when working with the RAG system, Reddit Tool (PRAW), or Moderation Tool
- Provide comprehensive pull request descriptions explaining the "what" and "why" of your changes

*For Documentation Contributors:*
- Create clear, beginner-friendly documentation that helps onboard new contributors
- Add examples and use cases where appropriate, particularly for the Portia AI framework integration
- Keep the RAG corpus (data/corpus/) up-to-date with accurate project information, as this directly impacts the quality of AI-generated responses

*For Issue Reporters:*
- Search existing issues before creating a new one to avoid duplicates
- Provide detailed, reproducible bug reports including:
  - Steps to reproduce the issue
  - Expected vs. actual behavior
  - Environment details (Python version, OS, relevant API credentials status)
  - Screenshots or logs where applicable
- For feature requests, explain the problem you're trying to solve and the proposed solution's benefits

*For AI-Related Interactions:*
- *Never approve AI-generated responses without careful review* – the human-in-the-loop (HITL) approval process is our most critical safety feature
- *Verify that RAG-grounded responses cite accurate documentation* and don't hallucinate information
- *Test moderation filters* to ensure they catch inappropriate content before it reaches human reviewers
- *Maintain data integrity* in the documentation corpus, as poor quality input leads to poor quality AI outputs

*For Cross-Platform Interactions (Reddit, Discord, Slack):*
- When the agent operates on public platforms like Reddit, remember you represent the project
- Be professional and helpful in all community support interactions
- Respect platform-specific rules and etiquette
- Never bypass the human approval process for automated responses
- Be transparent about when responses are AI-assisted vs. human-written

### Unacceptable Behavior

The following behaviors are unacceptable in our community:

- *Harassment or discrimination* of any kind, including but not limited to offensive comments related to personal characteristics
- *Trolling, insulting/derogatory comments*, and personal or political attacks
- *Public or private harassment*, including unwelcome sexual attention or advances
- *Publishing others' private information* (physical or email addresses) without explicit permission
- *Spam or promotional content* unrelated to the project
- *Deliberate disruption* of discussions or collaborative efforts

*Project-Specific Unacceptable Behaviors:*

- *Bypassing or disabling safety mechanisms*, including the HITL approval process or moderation filters
- *Submitting malicious code* or intentionally introducing vulnerabilities
- *Manipulating the RAG system* to inject false or misleading information into the documentation corpus
- *Attempting to use the agent for spam, harassment, or misinformation campaigns* on Reddit or other platforms
- *Sharing API credentials or access tokens* publicly, even in examples or documentation
- *Knowingly approving inaccurate AI-generated responses* for deployment
- *Creating fake or misleading issues, pull requests, or documentation*
- *Violating platform terms of service* (Reddit API, Discord, Slack) in your contributions or usage

---

##  Reporting Guidelines

### General Issues & Misconduct

If you experience or witness unacceptable behavior, or have any concerns, please report it as soon as possible.

*How to Report:*
1. *For urgent safety concerns*: Email the project maintainers directly at:
   - Benny Perumalla: benny01r@gmail.com
   - Md. Irshad Siddi: mohammadirshadsiddi@gmail.com

2. *For GitHub-related issues*: Open a private issue using GitHub's "Report content" feature, or email maintainers

3. *In your report, please include:*
   - Your contact information (optional, but helpful for follow-up)
   - Description of the incident, including dates, times, and specific behaviors
   - Any relevant screenshots, links, or documentation
   - Names of witnesses, if applicable
   - Any other information that might be helpful

### AI-Related Issues

Given the AI-powered nature of this project, we have specific reporting mechanisms for AI-related concerns:

*Report these immediately:*

1. *Incorrect RAG Output*
   - When the system retrieves wrong or irrelevant documentation
   - When citations are inaccurate or fabricated
   - When the agent "hallucinates" information not present in the corpus
   - *How*: Open a GitHub issue with the label rag-issue and include:
     - The query that triggered the problem
     - The incorrect output/citation
     - The expected correct information
     - Screenshots of the Streamlit UI showing the workflow

2. *Moderation Tool Failures*
   - When inappropriate content bypasses safety filters
   - When the moderation tool incorrectly flags acceptable content
   - *How*: Email maintainers immediately (do not post publicly if content is sensitive) or open a GitHub issue with label moderation-issue

3. *HITL Approval Process Issues*
   - If the system posts without human approval
   - If the approval workflow is unclear or confusing in the UI
   - If you're unable to reject problematic AI-generated responses
   - *How*: Open a GitHub issue with label hitl-issue and detailed steps to reproduce

4. *Reddit/Platform Integration Problems*
   - Authentication failures with Reddit API
   - Incorrect targeting of posts/subreddits
   - Rate limiting or API violations
   - *How*: Open a GitHub issue with label platform-integration and include your .env configuration (without exposing credentials)

5. *Data Quality Issues*
   - Outdated or incorrect documentation in data/corpus/
   - Missing crucial project information affecting response quality
   - *How*: Open a pull request to fix the corpus, or a GitHub issue with label documentation

*Quality Standards for Bug Reports:*

To maintain project quality and facilitate quick resolution, all bug reports should include:
- *Environment*: Python version, OS, dependency versions from requirements.txt
- *Reproduction steps*: Clear, numbered steps anyone can follow
- *Expected behavior*: What should happen
- *Actual behavior*: What actually happens
- *Logs/screenshots*: Output from the terminal or Streamlit UI
- *Impact*: How this affects the project's core mission of helping maintainers

---

##  Enforcement

### Our Responsibilities

Project maintainers are responsible for clarifying and enforcing our standards of acceptable behavior. They have the right and responsibility to remove, edit, or reject comments, commits, code, wiki edits, issues, and other contributions that are not aligned with this Code of Conduct.

Maintainers who do not follow or enforce the Code of Conduct in good faith may face temporary or permanent repercussions as determined by other members of the project's leadership.

### Enforcement Process

When a violation is reported, maintainers will:

1. *Acknowledge receipt* of the report within 48 hours
2. *Investigate* the issue by reviewing evidence and speaking with relevant parties
3. *Determine appropriate action* based on the severity and context of the violation
4. *Communicate the decision* to the reporter and the person who violated the code (when appropriate)
5. *Follow up* to ensure the issue is resolved and prevent future occurrences

### Enforcement Actions

Depending on the severity of the violation, maintainers may take the following actions:

#### 1. Correction (Minor Violations)
*Example*: Using inappropriate language or unprofessional behavior in a single instance
*Action*: A private, written warning explaining what was inappropriate and why, with a request to correct the behavior

#### 2. Warning (Moderate Violations)
*Example*: Violating community standards through a single incident or series of minor actions
*Action*: 
- A formal warning with consequences for continued behavior
- Temporary restriction from interacting with the community (e.g., 7-day comment ban)
- Required acknowledgment of the warning

#### 3. Temporary Ban (Serious Violations)
*Example*: Sustained inappropriate behavior, harassment, or deliberately compromising the AI safety mechanisms
*Action*:
- Temporary ban from all project interactions (30-90 days)
- No unsolicited contact with community members or maintainers during this period
- Automatic rejection of all contributions during the ban period
- Clear conditions for reinstatement

#### 4. Permanent Ban (Severe Violations)
*Example*: 
- Demonstrating a pattern of violation of community standards
- Deliberately sabotaging the project or its safety mechanisms
- Harassment, threats, or doxxing
- Attempting to use the agent for malicious purposes
*Action*:
- Permanent ban from all project spaces and interactions
- Public statement about the ban (when necessary for community safety)
- Potential reporting to GitHub and relevant platform authorities

### Appeals Process

If you believe an enforcement action was unjust, you may appeal by:
1. Sending an email to a maintainer not involved in the original decision
2. Providing new evidence or context not previously considered
3. Explaining why you believe the action was inappropriate

Appeals will be reviewed within 14 days by maintainers not involved in the original decision.

### Transparency & Accountability

- Enforcement actions will be documented internally to track patterns and ensure consistency
- Aggregate statistics (without identifying information) may be shared to demonstrate our commitment to community safety
- Maintainers will regularly review and update these enforcement procedures based on community feedback

---

##  Community Values for Long-Term Success

As we work toward our roadmap goals—integrating vector databases (ChromaDB/Milvus), expanding to Discord/Slack, and implementing metrics dashboards—we ask all contributors to embrace:

- *Scalability mindset*: Write code and documentation that will serve the project as it grows
- *Transparency commitment*: The planned metrics dashboard will show our impact; let's ensure all our work is honest and verifiable
- *Maintainer empathy*: Remember that reducing burnout is our core mission; treat maintainers' time as precious
- *Safety-first approach*: The human-in-the-loop model is non-negotiable; always prioritize safe, controllable AI

---

##  Attribution

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org/), version 2.1, available at https://www.contributor-covenant.org/version/2/1/code_of_conduct.html.

It has been customized for the OSS Community Agent project to address the unique aspects of AI-assisted community management, human-in-the-loop safety mechanisms, and cross-platform open-source collaboration.

Community Impact Guidelines were inspired by [Mozilla's code of conduct enforcement ladder](https://github.com/mozilla/diversity).

For answers to common questions about this code of conduct, see the FAQ at https://www.contributor-covenant.org/faq.

---

## Questions?

If you have questions about this Code of Conduct or need clarification on any point, please:
- Open a GitHub Discussion in the repository
- Email the maintainers (contact information in the README)
- Suggest improvements via a pull request

*Last Updated*: October 2025

*Version*: 1.0.0

---

Thank you for helping us build a welcoming, safe, and innovative community around the OSS Community Agent project. Together, we can make open-source maintenance more sustainable for everyone!
