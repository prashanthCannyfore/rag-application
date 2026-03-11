"""
Generate a second test resume PDF
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# Create a professional resume
c = canvas.Canvas("test_resume2.pdf", pagesize=letter)
width, height = letter

# Header
c.setFont("Helvetica-Bold", 20)
c.drawString(1 * inch, height - 1 * inch, "Sarah Smith")

c.setFont("Helvetica", 12)
c.drawString(1 * inch, height - 1.3 * inch, "Data Scientist | sarah.smith@email.com | (555) 987-6543")
c.drawString(1 * inch, height - 1.5 * inch, "LinkedIn: linkedin.com/in/sarahsmith | GitHub: github.com/sarahsmith")

# Summary
c.setFont("Helvetica-Bold", 14)
c.drawString(1 * inch, height - 2 * inch, "PROFESSIONAL SUMMARY")
c.setFont("Helvetica", 10)
text = c.beginText(1 * inch, height - 2.2 * inch)
text.setLeading(14)
text.textLine("Data scientist with 4+ years of experience in machine learning and data analysis.")
text.textLine("Expert in Python, SQL, and machine learning frameworks. Skilled at transforming raw data")
text.textLine("into actionable insights that drive business decisions.")
c.drawText(text)

# Skills
c.setFont("Helvetica-Bold", 14)
c.drawString(1 * inch, height - 3 * inch, "TECHNICAL SKILLS")
c.setFont("Helvetica", 10)
text = c.beginText(1 * inch, height - 3.2 * inch)
text.setLeading(14)
text.textLine("• Python, SQL, R")
text.textLine("• Scikit-learn, TensorFlow, PyTorch")
text.textLine("• Pandas, NumPy, Matplotlib, Seaborn")
text.textLine("• AWS SageMaker, Google Cloud AI")
text.textLine("• SQL, BigQuery, Snowflake")
text.textLine("• Tableau, Power BI")
c.drawText(text)

# Experience
c.setFont("Helvetica-Bold", 14)
c.drawString(1 * inch, height - 4.5 * inch, "EXPERIENCE")

c.setFont("Helvetica-Bold", 11)
c.drawString(1 * inch, height - 4.8 * inch, "Data Scientist | AnalyticsCo | 2020 - Present")
c.setFont("Helvetica", 10)
text = c.beginText(1 * inch, height - 5 * inch)
text.setLeading(14)
text.textLine("• Developed predictive models that improved customer retention by 25%")
text.textLine("• Created automated reporting dashboards using Tableau and Power BI")
text.textLine("• Performed A/B testing to optimize marketing campaigns")
text.textLine("• Collaborated with product teams to define key metrics")
c.drawText(text)

c.setFont("Helvetica-Bold", 11)
c.drawString(1 * inch, height - 6 * inch, "Junior Data Analyst | DataFirm | 2018 - 2020")
c.setFont("Helvetica", 10)
text = c.beginText(1 * inch, height - 6.2 * inch)
text.setLeading(14)
text.textLine("• Cleaned and analyzed large datasets using SQL and Python")
text.textLine("• Created visualizations to communicate insights to stakeholders")
text.textLine("• Supported senior analysts with model development")
c.drawText(text)

# Education
c.setFont("Helvetica-Bold", 14)
c.drawString(1 * inch, height - 7.5 * inch, "EDUCATION")
c.setFont("Helvetica", 11)
c.drawString(1 * inch, height - 7.8 * inch, "Master of Science in Data Science")
c.setFont("Helvetica", 10)
c.drawString(1 * inch, height - 8 * inch, "University of Data | 2016 - 2018")
c.drawString(1 * inch, height - 8.2 * inch, "GPA: 3.9/4.0 | Specialized in Machine Learning")

c.save()

print("Resume created: test_resume2.pdf")
print("This resume contains data science experience, skills, and education information.")
