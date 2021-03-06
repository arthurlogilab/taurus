
import tempfile

import yaml
from tests import BZTestCase
from bzt.jmx2yaml import JMX2YAML
from tests.mocks import EngineEmul, RecordingHandler


class FakeOptions(object):
    def __init__(self, verbose=True, file_name=None, dump_jmx=False, quiet=False, json=False, log=False):
        self.verbose = verbose
        self.file_name = file_name
        self.dump_jmx = dump_jmx
        self.quiet = quiet
        self.json = json
        self.log = log


class TestConverter(BZTestCase):
    def temp_yaml(self):
        emul = EngineEmul()
        return emul.create_artifact("test", ".yml")

    def test_loadjmx1(self):
        log_recorder = RecordingHandler()
        obj = JMX2YAML(FakeOptions(file_name=self.temp_yaml()), "tests/jmx/http.jmx")
        obj.log.addHandler(log_recorder)
        obj.process()
        self.assertIn("Loading jmx file", log_recorder.info_buff.getvalue())
        self.assertNotEqual("", log_recorder.debug_buff.getvalue())
        self.assertEqual("", log_recorder.err_buff.getvalue())
        obj.log.removeHandler(log_recorder)

    def test_loadjmx2(self):
        log_recorder = RecordingHandler()
        obj = JMX2YAML(FakeOptions(), "tests/jmx/notfound.jmx")
        obj.log.addHandler(log_recorder)
        try:
            obj.process()
            self.fail()
        except BaseException as exc:
            self.assertIn("File does not exist", exc.args[0])
        self.assertIn("Loading jmx file", log_recorder.info_buff.getvalue())
        self.assertIn("does not exist", log_recorder.err_buff.getvalue())
        self.assertEqual("", log_recorder.debug_buff.getvalue())
        obj.log.removeHandler(log_recorder)

    def test_loadjmx3(self):
        log_recorder = RecordingHandler()
        obj = JMX2YAML(FakeOptions(), "tests/jmx/broken.jmx")
        obj.log.addHandler(log_recorder)
        try:
            obj.process()
            self.fail()
        except BaseException as exc:
            self.assertIn("XML parsing failed", exc.args[0])
        self.assertIn("Loading jmx file", log_recorder.info_buff.getvalue())
        self.assertIn("Error while processing jmx file", log_recorder.err_buff.getvalue())
        self.assertIn("XML parsing error", log_recorder.debug_buff.getvalue())
        obj.log.removeHandler(log_recorder)

    def test_loadjmx4(self):
        log_recorder = RecordingHandler()
        with tempfile.NamedTemporaryFile() as tmp_file:
            obj = JMX2YAML(FakeOptions(file_name=tmp_file.name), "tests/jmx/http.jmx")
            obj.log.addHandler(log_recorder)
            obj.process()
            self.assertIn("Loading jmx file", log_recorder.info_buff.getvalue())
            self.assertIn("Done processing, result saved in", log_recorder.info_buff.getvalue())
            self.assertIn("Removing unknown element", log_recorder.warn_buff.getvalue())
            obj.log.removeHandler(log_recorder)

    def test_export_clean_jmx(self):
        with tempfile.NamedTemporaryFile() as tmp_jmx:
            obj = JMX2YAML(FakeOptions(dump_jmx=tmp_jmx.name, file_name=self.temp_yaml()),
                           "tests/yaml/converter/disabled.jmx")
            log_recorder = RecordingHandler()
            obj.log.addHandler(log_recorder)
            obj.process()

            self.assertIn("Loading jmx file", log_recorder.info_buff.getvalue())
            self.assertIn("already exists and will be overwritten", log_recorder.warn_buff.getvalue())
            obj.log.removeHandler(log_recorder)

    def test_not_jmx(self):
        obj = JMX2YAML(FakeOptions(file_name=self.temp_yaml()), "tests/jmx/not-jmx.xml")
        try:
            obj.process()
            self.fail()
        except BaseException as exc:
            self.assertIn("Bad jmx format", exc.args[0])

    def test_clean_disabled_jmx(self):
        obj = JMX2YAML(FakeOptions(file_name=self.temp_yaml()), "tests/yaml/converter/disabled.jmx")
        obj.process()
        disabled_elements = [element for element in obj.converter.dialect.tree.iter() if
                             element.get("enabled") == "false"]
        self.assertEquals(0, len(disabled_elements))

    def test_copy_global_csv_dataset(self):
        yml = self.temp_yaml()
        obj = JMX2YAML(FakeOptions(file_name=yml), "tests/yaml/converter/global_copy.jmx")
        obj.process()
        yml = yaml.load(open(yml).read())
        datasets_first_tg = yml.get("scenarios").get("Thread Group one").get("data-sources")
        datasets_second_tg = yml.get("scenarios").get("Thread Group two").get("data-sources")

        global_csv_tg_one = [dataset for dataset in datasets_first_tg if dataset.get('path') == 'global.csv']
        global_csv_tg_two = [dataset for dataset in datasets_second_tg if dataset.get('path') == 'global.csv']

        local_csv_tg_one = [dataset for dataset in datasets_first_tg if dataset.get('path') == 'local.csv']
        local_csv_tg_two = [dataset for dataset in datasets_second_tg if dataset.get('path') == 'local.csv']
        self.assertEqual(len(global_csv_tg_one), len(global_csv_tg_two), 1)
        self.assertEqual(len(local_csv_tg_one), 1)
        self.assertEqual(len(local_csv_tg_two), 0)

    def test_copy_global_headers(self):
        yml = self.temp_yaml()
        obj = JMX2YAML(FakeOptions(file_name=yml), "tests/yaml/converter/global_copy.jmx")
        obj.process()
        yml = yaml.load(open(yml).read())
        headers_first_tg = yml.get("scenarios").get("Thread Group one").get("headers", [])
        headers_second_tg = yml.get("scenarios").get("Thread Group two").get("headers", [])
        self.assertEqual(len(headers_first_tg), 3)
        self.assertEqual(len(headers_second_tg), 2)

    def test_cache_cookie_dns_overrides(self):
        yml = self.temp_yaml()
        obj = JMX2YAML(FakeOptions(file_name=yml), "tests/yaml/converter/global_copy.jmx")
        obj.process()
        yml = yaml.load(open(yml).read())
        tg_one = yml.get("scenarios").get('Thread Group one')
        tg_two = yml.get("scenarios").get('Thread Group two')
        cache_first_tg = tg_one.get("store-cache")
        cache_second_tg = tg_two.get("store-cache")
        cookie_first_tg = tg_one.get("store-cookie")
        cookie_second_tg = tg_two.get("store-cookie")
        dns_cache_mgr_first_tg = tg_one.get("use-dns-cache-mgr")
        dns_cache_mgr_second_tg = tg_two.get("use-dns-cache-mgr")
        self.assertEqual(cache_first_tg, True)
        self.assertEqual(cache_second_tg, True)
        self.assertEqual(cookie_first_tg, False)
        self.assertEqual(cookie_second_tg, True)
        self.assertEqual(dns_cache_mgr_first_tg, True)
        self.assertEqual(dns_cache_mgr_second_tg, True)

    def test_think_time_overrides(self):
        yml = self.temp_yaml()
        obj = JMX2YAML(FakeOptions(file_name=yml), "tests/yaml/converter/global_copy.jmx")
        obj.process()
        yml = yaml.load(open(yml).read())
        tg_one = yml.get("scenarios").get('Thread Group one')
        tg_two = yml.get("scenarios").get('Thread Group two')
        request_tg_two = tg_two.get("requests")[0]
        tg_one_timer = tg_one.get("think-time")
        tg_two_timer = tg_two.get("think-time")
        req_timer = request_tg_two.get("think-time")

        self.assertEqual(tg_one_timer, "200ms")
        self.assertEqual(tg_two_timer, "300ms")
        self.assertEqual(req_timer, "100ms")

    def test_request_defaults(self):
        yml = self.temp_yaml()
        obj = JMX2YAML(FakeOptions(file_name=yml), "tests/yaml/converter/global_copy.jmx")
        obj.process()
        yml = yaml.load(open(yml).read())
        tg_one = yml.get("scenarios").get('Thread Group one')
        tg_two = yml.get("scenarios").get('Thread Group two')
        self.assertEqual(tg_one.get("default-address"), "https://127.0.0.2/")
        self.assertEqual(tg_two.get("default-address"), "http://127.0.0.3:2582/resources/")
        self.assertEqual(tg_one.get("timeout"), "500ms")
        self.assertEqual(tg_two.get("timeout"), "100ms")
        self.assertEqual(tg_one.get("retrieve-resources"), True)
        self.assertEqual(tg_two.get("retrieve-resources"), True)
        self.assertEqual(tg_one.get("concurrent-pool-size"), 5)
        self.assertEqual(tg_two.get("concurrent-pool-size"), 10)

    def test_copy_global_request_assertions(self):
        yml = self.temp_yaml()
        obj = JMX2YAML(FakeOptions(file_name=yml), "tests/yaml/converter/assertions.jmx")
        obj.process()
        yml = yaml.load(open(yml).read())
        tg_one = yml.get("scenarios").get("tg1")
        tg_two = yml.get("scenarios").get("tg2")
        tg_one_assertions = tg_one.get("assert")
        self.assertEqual(len(tg_one_assertions), 2)  # global assertion + tg assertion
        tg_two_assertions = tg_two.get("assert")
        self.assertEqual(len(tg_two_assertions), 1)  # global only assertion
        tg_one_req_one_assertion = tg_one.get("requests")[0].get("assert")[0]
        expected = {'subject': 'headers', 'contains': ["tg1httpreq1", "tg1httpreq12"], "not": False, 'regexp': True}
        self.assertEqual(tg_one_req_one_assertion, expected)
        tg_one_assertion = tg_one.get("assert")[0]
        expected = {'subject': 'body', 'contains': ["tg1body_text_not_contains"], "not": True, 'regexp': True}
        self.assertEqual(tg_one_assertion, expected)

    def test_copy_global_json_assertions(self):
        yml = self.temp_yaml()
        obj = JMX2YAML(FakeOptions(file_name=yml), "tests/yaml/converter/assertions.jmx")
        obj.process()
        yml = yaml.load(open(yml).read())
        tg_one = yml.get("scenarios").get("tg1")
        tg_two = yml.get("scenarios").get("tg2")
        tg_one_assertions = tg_one.get("assert-jsonpath")
        self.assertEqual(len(tg_one_assertions), 1)  # global assertion + tg assertion
        tg_two_assertions = tg_two.get("assert-jsonpath")
        self.assertEqual(len(tg_two_assertions), 1)  # global only assertion
        tg_one_req_one_jp = tg_one.get("requests")[0].get("assert-jsonpath", [])  # no assertions
        self.assertEqual(len(tg_one_req_one_jp), 0)
        tg_two_req_one_jp = tg_two.get("requests")[0].get("assert-jsonpath", [])
        self.assertEqual(len(tg_two_req_one_jp), 1)
        expected = {"expect-null": True, "invert": True, "jsonpath": '$(":input")', "validate": True}
        self.assertEqual(expected, tg_two_req_one_jp[0])
        #  test concurrency, ramp-up, iterations in execution
        tg_one_exec = yml.get("execution")[0]
        tg_two_exec = yml.get("execution")[1]
        tg_three_exec = yml.get("execution")[2]
        self.assertEqual(tg_one_exec.get("concurrency"), 10)
        self.assertEqual(tg_two_exec.get("concurrency"), 15)
        self.assertEqual(tg_three_exec.get("concurrency"), None)
        self.assertEqual(tg_one_exec.get("ramp-up"), '10s')
        self.assertEqual(tg_two_exec.get("ramp-up"), None)
        self.assertEqual(tg_three_exec.get("ramp-up"), '2s')
        self.assertEqual(tg_one_exec.get("iterations"), None)
        self.assertEqual(tg_two_exec.get("iterations"), None)
        self.assertEqual(tg_three_exec.get("iterations"), 100)

    def test_extractors(self):
        yml = self.temp_yaml()
        obj = JMX2YAML(FakeOptions(file_name=yml), "tests/yaml/converter/extractors.jmx")
        obj.process()
        yml = yaml.load(open(yml).read())
        tg_one = yml.get("scenarios").get("tg1")
        tg_two = yml.get("scenarios").get("tg2")
        tg_three = yml.get("scenarios").get("tg3")
        tg_one_extractors = tg_one.get("extract-regexp")
        tg_two_extractors = tg_two.get("extract-regexp")
        self.assertEqual(len(tg_one_extractors), 1)  # global
        self.assertEqual(len(tg_two_extractors), 1)  # global + local - ignored
        tg_one_req_exr = tg_one.get("requests")[0].get("extract-regexp", {})
        self.assertEqual(len(tg_one_req_exr), 2)
        expected = {'template': '1', 'match-no': 1, 'regexp': '*tg1hr1', 'default': 'default'}
        self.assertEqual(expected, tg_one_req_exr.get("test_tg1hr1"))
        # test extract-jsonpath
        tg_one_extractors = tg_one.get("extract-jsonpath")
        tg_two_extractors = tg_two.get("extract-jsonpath")
        self.assertEqual(len(tg_one_extractors), 3)  # 2x global + local
        self.assertEqual(len(tg_two_extractors), 2)  # 2x global
        tg_three_req_exr = tg_three.get("requests")[0].get("extract-jsonpath", {})
        self.assertEqual(len(tg_three_req_exr), 1)  # 1x local

    def test_request_body(self):
        yml = self.temp_yaml()
        obj = JMX2YAML(FakeOptions(file_name=yml), "tests/yaml/converter/extractors.jmx")
        obj.process()
        yml = yaml.load(open(yml).read())
        tg_one = yml.get("scenarios").get("tg1")
        tg_two = yml.get("scenarios").get("tg2")
        tg_one_req_one_body = tg_one.get("requests")[0].get("body")
        self.assertEqual(tg_one_req_one_body, "body-string")
        tg_one_req_one_body = tg_one.get("requests")[1].get("body")
        self.assertEqual(tg_one_req_one_body, {"body_param1": "value1", "body_param2": "value2"})
        tg_two_req_one_body = tg_two.get("requests")[0].get("body")
        self.assertEqual(tg_two_req_one_body, None)

    def test_duration_throughput(self):
        yml = self.temp_yaml()
        obj = JMX2YAML(FakeOptions(file_name=yml), "tests/yaml/converter/duration.jmx")
        obj.process()
        yml = yaml.load(open(yml).read())
        tg_one = yml.get("execution")[0]
        tg_two = yml.get("execution")[1]
        tg_three = yml.get("execution")[2]
        self.assertEqual("10s", tg_one.get("ramp-up"))
        self.assertEqual(None, tg_one.get("hold-for"))
        self.assertEqual("10s", tg_one.get("ramp-up"))
        self.assertEqual(100, tg_one.get("throughput"))
        self.assertEqual("10s", tg_two.get("ramp-up"))
        self.assertEqual("20s", tg_two.get("hold-for"))
        self.assertEqual(20, tg_two.get("throughput"))
        self.assertEqual(None, tg_three.get("ramp-up"))
        self.assertEqual("40s", tg_three.get("hold-for"))
        self.assertEqual(100, tg_three.get("throughput"))

    def test_all(self):
        obj = JMX2YAML(FakeOptions(file_name=self.temp_yaml()), "tests/yaml/converter/disabled.jmx")
        obj.process()
        yml = yaml.load(open("tests/yaml/converter/disabled.yml").read())
        self.assertEqual(obj.converter.convert(obj.file_to_convert), yml)
