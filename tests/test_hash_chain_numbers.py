"""A line's hash is the reference implementation's: numbers as JavaScript writes them.

dil-core hashes `JSON.stringify(record)`. Until 2026-10-19 this port hashed floats
as Python writes them (`1.0`, where JavaScript writes `1`), so every log it wrote
broke under dil-core's verifier at its first expectation. The texts and the hash
expected here were computed by node (`JSON.stringify`, `crypto.createHash`).
"""

import json
import unittest

from dil.store import CHAIN_GENESIS, SCHEMA_VERSION, ChainBroken, ChainOk, verify_chain
from dil.store.hash_chain import (
    ChainedEventLine,
    _canonical_json,
    _python_hash,
    chain_next,
    hash_chain_entry,
)

# An expectation as this host writes it: `confidence` and `delta` are floats.
EXPECTATION = {
    "form": "expectation", "datumId": "cycle-0", "cycleMark": 0, "entity": "frame", "source": "frame",
    "confidence": 0.0, "recurrence": 0, "delta": 1.0, "t": 1792386185615,
}
# node: sha256(`0\n${"0".repeat(64)}\n4\n${JSON.stringify(EXPECTATION)}`)
JS_HASH = "792cb1e47477449449881af324b93b98ef321243a09aa6a896de21e50b05e075"


class NumbersAsJavaScriptWritesThem(unittest.TestCase):
    def test_each_float_is_written_as_json_stringify_writes_it(self) -> None:
        # node: JSON.stringify(v) for each v
        cases = {
            1.0: "1", -0.0: "0", 0.5: "0.5", 1e-4: "0.0001", 1e-5: "0.00001", 1.5e-7: "1.5e-7",
            1e21: "1e+21", 1e20: "100000000000000000000", 2.0**53 + 2: "9007199254740994",
            123.456: "123.456", -2.5e-8: "-2.5e-8",
        }
        for value, text in cases.items():
            self.assertEqual(_canonical_json(value), text, value)

    def test_a_string_is_left_as_it_is_and_integers_stand(self) -> None:
        value = {"s": "1.0 and 2.5e-07", "q": 'a"1.0', "n": [1, 2.0, -3], "e": True}
        self.assertEqual(_canonical_json(value), '{"s":"1.0 and 2.5e-07","q":"a\\"1.0","n":[1,2,-3],"e":true}')

    def test_the_hash_is_dil_cores(self) -> None:
        self.assertEqual(hash_chain_entry(0, CHAIN_GENESIS, 4, EXPECTATION), JS_HASH)

    def test_a_line_written_before_verifies_by_its_form_and_is_counted(self) -> None:
        line = chain_next(CHAIN_GENESIS, 0, EXPECTATION)
        old = ChainedEventLine(seq=0, prev=CHAIN_GENESIS, schema_version=4, record=EXPECTATION,
                               hash=_python_hash(0, CHAIN_GENESIS, 4, EXPECTATION))
        self.assertNotEqual(old.hash, line.hash)
        self.assertEqual(verify_chain([line]), ChainOk(count=1, head=line.hash, legacy=0))
        self.assertEqual(verify_chain([old]), ChainOk(count=1, head=old.hash, legacy=1))

    def test_an_altered_record_breaks_under_either_form(self) -> None:
        old = ChainedEventLine(seq=0, prev=CHAIN_GENESIS, schema_version=4, record=EXPECTATION,
                               hash=_python_hash(0, CHAIN_GENESIS, 4, EXPECTATION))
        altered = ChainedEventLine(seq=0, prev=CHAIN_GENESIS, schema_version=4,
                                   record={**EXPECTATION, "delta": 0.0}, hash=old.hash)
        self.assertIsInstance(verify_chain([altered]), ChainBroken)

    def test_a_float_that_is_not_finite_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            _canonical_json({"x": float("nan")})

    def test_the_line_as_written_reads_back_to_the_same_hash(self) -> None:
        line = chain_next(CHAIN_GENESIS, 0, EXPECTATION)
        record = json.loads(json.dumps(line.record))
        self.assertEqual(hash_chain_entry(0, CHAIN_GENESIS, SCHEMA_VERSION, record), line.hash)


if __name__ == "__main__":
    unittest.main()
