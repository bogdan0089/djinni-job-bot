from app.schemas.job import Vacancy
from app.utils.text import TELEGRAM_MESSAGE_LIMIT, build_vacancy_messages


class TestVacancyRendering:
    def test_escapes_html_in_titles(self) -> None:
        line = Vacancy(title="C++ <b>Dev</b>", url="https://x").as_message_line()
        assert "&lt;b&gt;" in line
        assert "<b>Dev</b>" not in line

    def test_escapes_quotes_in_urls(self) -> None:
        line = Vacancy(title="Dev", url='https://x/"onmouseover=').as_message_line()
        assert '"onmouseover=' not in line
        assert "&quot;" in line

    def test_renders_a_clickable_link(self) -> None:
        line = Vacancy(title="Dev", url="https://djinni.co/jobs/1").as_message_line()
        assert line == '• <a href="https://djinni.co/jobs/1">Dev</a>'


class TestMessageBuilding:
    def test_no_vacancies_produces_no_messages(self) -> None:
        assert build_vacancy_messages([]) == []

    def test_all_vacancies_fit_in_one_message(self) -> None:
        vacancies = [Vacancy(title=f"Dev {i}", url=f"https://x/{i}") for i in range(10)]
        messages = build_vacancy_messages(vacancies, header="<b>10 jobs</b>")
        assert len(messages) == 1
        assert messages[0].startswith("<b>10 jobs</b>")
        assert messages[0].count("\n") == 10

    def test_long_list_is_split_and_every_chunk_fits_the_limit(self) -> None:
        vacancies = [
            Vacancy(title="D" * 200, url=f"https://djinni.co/jobs/{i}") for i in range(60)
        ]
        messages = build_vacancy_messages(vacancies)
        assert len(messages) > 1
        assert all(len(m) <= TELEGRAM_MESSAGE_LIMIT for m in messages)

    def test_nothing_is_lost_when_splitting(self) -> None:
        vacancies = [
            Vacancy(title="D" * 200, url=f"https://djinni.co/jobs/{i}") for i in range(60)
        ]
        joined = "\n".join(build_vacancy_messages(vacancies))
        assert joined.count("djinni.co/jobs/") == 60
