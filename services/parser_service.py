import aiohttp
from bs4 import BeautifulSoup


class ParserService:

    async def get_djinni_jobs(self, stack: str = None, experience: str = None) -> list[dict]:
        words = [w.strip() for w in stack.replace(",", " ").split() if w.strip()] if stack else ["Python"]
        keyword = words[0]
        url = f"https://djinni.co/jobs/rss/?primary_keyword={keyword}"
        exp_map={
            "junior": "1y",
            "middle": "3y",
            "senior": "5y"
        }
        if experience:
            url += f"&exp_level={exp_map.get(experience, '1y')}"

        headers = {"User-Agent": "Mozilla/5.0"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                xml = await response.text()

        soup = BeautifulSoup(xml, "xml")
        jobs = []

        for item in soup.select("item")[:10]:
            title = item.find("title")
            link = item.find("link")

            jobs.append({
                "title": title.text.strip() if title else "N/A",
                "url": link.text.strip() if link else "N/A"
            })

        if experience in ("junior", "middle"):
            exclude = ["senior", "lead", "staff", "principal"]
            jobs = [j for j in jobs if not any(w in j["title"].lower() for w in exclude)]

        return jobs
