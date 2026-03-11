"""
Generate a test resume PDF
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# Create a professional resume
c = canvas.Canvas("test_resume.pdf", pagesize=letter)
width, height = letter

# Header
c.setFont("Helvetica-Bold", 20)
c.drawString(1 * inch, height - 1 * inch, "John Doe")

c.setFont("Helvetica", 12)
c.drawString(1 * inch, height - 1.3 * inch, "Software Engineer | john.doe@email.com | (555) 123-4567")
c.drawString(1 * inch, height - 1.5 * inch, "LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe")

# Summary
c.setFont("Helvetica-Bold", 14)
c.drawString(1 * inch, height - 2 * inch, "PROFESSIONAL SUMMARY")
c.setFont("Helvetica", 10)
text = c.beginText(1 * inch, height - 2.2 * inch)
text.setLeading(14)
text.textLine("Results-driven software engineer with 5+ years of experience in building scalable web applications.")
text.textLine("Expert in Python, JavaScript, and cloud technologies. Proven track record of delivering high-quality")
text.textLine("software solutions that improve business efficiency by 30%+.")
c.drawText(text)

# Skills
c.setFont("Helvetica-Bold", 14)
c.drawString(1 * inch, height - 3 * inch, "TECHNICAL SKILLS")
c.setFont("Helvetica", 10)
text = c.beginText(1 * inch, height - 3.2 * inch)
text.setLeading(14)
text.textLine("• Python, JavaScript, TypeScript")
text.textLine("• Django, Flask, FastAPI, React, Node.js")
text.textLine("• PostgreSQL, MySQL, MongoDB, Redis")
text.textLine("• Docker, Kubernetes, AWS, Azure")
text.textLine("• Git, CI/CD, Agile/Scrum")
c.drawText(text)

# Experience
c.setFont("Helvetica-Bold", 14)
c.drawString(1 * inch, height - 4.5 * inch, "EXPERIENCE")

c.setFont("Helvetica-Bold", 11)
c.drawString(1 * inch, height - 4.8 * inch, "Senior Software Engineer | TechCorp Inc. | 2021 - Present")
c.setFont("Helvetica", 10)
text = c.beginText(1 * inch, height - 5 * inch)
text.setLeading(14)
text.textLine("• Led a team of 5 developers building a microservices architecture")
text.textLine("• Reduced API response time by 40% through database optimization")
text.textLine("• Implemented CI/CD pipelines reducing deployment time by 60%")
text.textLine("• Mentored junior developers and conducted code reviews")
c.drawText(text)

c.setFont("Helvetica-Bold", 11)
c.drawString(1 * inch, height - 6 * inch, "Software Developer | StartupXYZ | 2018 - 2021")
c.setFont("Helvetica", 10)
text = c.beginText(1 * inch, height - 6.2 * inch)
text.setLeading(14)
text.textLine("• Developed RESTful APIs using Python and Flask")
text.textLine("• Integrated third-party payment gateways (Stripe, PayPal)")
text.textLine("• Built real-time features using WebSockets and Redis")
c.drawText(text)

# Education
c.setFont("Helvetica-Bold", 14)
c.drawString(1 * inch, height - 7.5 * inch, "EDUCATION")
c.setFont("Helvetica", 11)
c.drawString(1 * inch, height - 7.8 * inch, "Bachelor of Science in Computer Science")
c.setFont("Helvetica", 10)
c.drawString(1 * inch, height - 8 * inch, "University of Technology | 2014 - 2018")
c.drawString(1 * inch, height - 8.2 * inch, "GPA: 3.8/4.0 | Dean's List")

c.save()

print("Resume created: test_resume.pdf")
print("This resume contains professional experience, skills, and education information.")
