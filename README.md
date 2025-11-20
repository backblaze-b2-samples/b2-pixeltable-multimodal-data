# Backblaze B2 + Pixeltable Examples

Example notebooks demonstrating how to use **[Pixeltable](https://www.pixeltable.com/)** with **[Backblaze B2 Cloud Storage](https://www.backblaze.com/cloud-storage)** for multimodal data processing and AI workflows.

These examples show how to manage and process image and video data directly from B2, perform AI-driven transformations, and store the results back in cloud storage with automatic URL generation.

---

## Included Notebooks

### [Multimodal Data Processing with Pixeltable and Backblaze B2](01-video-frames-b2.ipynb)
Learn how to extract video frames, transform them (e.g., grayscale conversion or AI-based editing), and store the results in Backblaze B2.

---

## About Pixeltable

**[Pixeltable](https://www.pixeltable.com/)** is an open-source AI data infrastructure that enables:

- **Computed Columns:** Automate data processing with AI models and transformations  
- **Multimodal Support:** Work with images, video, audio, and documents in one framework  
- **Declarative Storage:** Define where to store data and Pixeltable handles uploads and URL generation  
- **Persistent Storage:** Maintain data and results across sessions  

Learn more in the [Pixeltable documentation](https://docs.pixeltable.com/overview/pixeltable).

---

## About Backblaze B2

**[Backblaze B2](https://www.backblaze.com/cloud-storage)** is cost-effective, S3-compatible cloud storage designed for simplicity and performance. It integrates seamlessly with Pixeltable using standard S3 endpoints (`https://s3.{region}.backblazeb2.com/`).

**Key Benefits:**
- **S3-compatible API:** Works seamlessly with Pixeltable’s storage system  
- **Cost-effective:** Competitive pricing for scalable cloud storage  
- **Simple setup:** Minimal configuration required  
- **Automatic URL generation:** Pixeltable generates accessible URLs for stored outputs  

**Prerequisites:** Backblaze B2 account (free tier available) and Python 3.9+

---
