# Backblaze B2 + Pixeltable Examples

Example notebooks demonstrating how to use **[Pixeltable](https://www.pixeltable.com/)** with **[Backblaze B2 Cloud Storage](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=pixeltable)** for multimodal data processing and AI workflows.

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

**[Backblaze B2 Cloud Storage](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=pixeltable)** is cost-effective, S3-compatible cloud storage designed for simplicity and performance. It integrates seamlessly with Pixeltable using standard S3 endpoints (`https://s3.{region}.backblazeb2.com/`).

**Key Benefits:**
- **S3-compatible API:** Works seamlessly with Pixeltable’s storage system  
- **Cost-effective:** Competitive pricing for scalable cloud storage  
- **Simple setup:** Minimal configuration required  
- **Automatic URL generation:** Pixeltable generates accessible URLs for stored outputs  

**Prerequisites:** Backblaze B2 account (free tier available) and Python 3.10+

## B2 Configuration

The notebook uses Backblaze B2 through the S3-compatible API by default. Configure
the sample with these user-facing environment variables:

```bash
B2_APPLICATION_KEY_ID=your-application-key-id
B2_APPLICATION_KEY=your-application-key
B2_BUCKET_NAME=your-bucket-name
B2_REGION=your-bucket-region
B2_PUBLIC_URL_BASE=https://s3.your-bucket-region.backblazeb2.com/your-bucket-name
```

`B2_PUBLIC_URL_BASE` is the base URL Pixeltable writes generated assets under.
If omitted, the notebook builds it from the selected region and bucket. If set,
it must be an HTTPS Backblaze B2 URL rooted at the selected bucket. The notebook
configures the Backblaze sample user agent on both its preflight S3 client and
Pixeltable's delegated S3 clients, then runs a bounded bucket preflight before
frame processing starts. Previous key-id and bucket variable names are accepted
for a transition period, but new automation should use the standard names above.

---
