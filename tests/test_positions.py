from app.results.domain.positions import classify_position


class TestClassifyPosition:
    def test_finished(self):
        assert classify_position(1) == "finished"
        assert classify_position("12") == "finished"
        assert classify_position("3.0") == "finished"

    def test_dns_dropped(self):
        assert classify_position("DNS") == "dns"
        assert classify_position("Did Not Start") == "dns"

    def test_dnf_kept(self):
        assert classify_position("DNF") == "dnf"
        assert classify_position("Did Not Finish") == "dnf"