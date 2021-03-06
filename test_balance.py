
""" Perform tests on the balance.py
"""

import unittest
import datetime
from datetime import date as Date
import json

from unittest import mock  # pragma: no cover
from io import StringIO

import balance


class fakedatetime(datetime.datetime):

    @classmethod
    def now(cls):
        # This is similar to cls(1990, 5, 4, 12, 12, 12) but the unix
        # timestamp is defined as UTC, and thus it is not a time that
        # floats around depending on which timezone is specified.
        # The timestamp value can be checked/confirmed with these
        # cmdlines:
        #       date --date @641823132 --iso-8601=seconds
        #       date --date @641823132 --iso-8601=seconds --utc
        #
        return cls.utcfromtimestamp(641823132)


class TestTime(unittest.TestCase):

    def test_iso8601(self):
        self.assertEqual(
            balance._iso8601_str(fakedatetime.now()),
            "1990-05-04T20:12:12+08:00"
            )


class TestSubp(unittest.TestCase):
    input_data = """
#balance 0 Opening Balance
500 1990-04-03 #dues:test1
20 1990-04-03 Unknown
1500 1990-04-27 #fridge
-12500 1990-04-15 #bills:rent
-1174 1990-04-27 #bills:electricity
-1500 1990-04-26 #fridge
500 1990-05-02 #dues:test1 !locn:test_location
-488 1990-05-25 #bills:internet
13152 1990-05-25 balance books
0 1990-05-14 !locn_xfer:test_location:test_location2:200
#balance 10 Closing balance
"""

    def setUp(self):
        f = StringIO(self.input_data)
        self.rows = balance.RowSet()
        self.rows.load_file(f)
        self.verbose = 1

    def tearDown(self):
        self.rows = None

    def test_sum(self):
        self.assertEqual(balance.subp_sum(self), "10")

        self.rows.append(
            balance.RowData( "-20", Date(1990, 5,26), "make total negative") # noqa
        )
        with self.assertRaises(ValueError):
            balance.subp_sum(self)

    def test_topay(self):
        expect = [
            "Date: 1990-04",
            "Bill                    Price   Pay Date",
            "Bills:electricity       -1174   1990-04-27",
            "Bills:internet          $0      Not Yet",
            "Bills:rent              -12500  1990-04-15",
            "Fridge                  -1500   1990-04-26",
            "",
            "Date: 1990-05",
            "Bill                    Price   Pay Date",
            "Bills:electricity       $0      Not Yet",
            "Bills:internet          -488    1990-05-25",
            "Bills:rent              $0      Not Yet",
            "Fridge                  $0      Not Yet",
            "",
            "",
        ]
        got = balance.subp_topay(self).split("\n")
        self.assertEqual(got, expect)

    def test_topay_html(self):
        expect = [
            "<h2>Date: <i>1990-04</i></h2>",
            "<table>",
            "<tr><th>Bills</th><th>Price</th><th>Pay Date</th></tr>",
            "",
            "    <tr>",
            "        "
            "<td>Bills:electricity</td><td>-1174</td><td>1990-04-27</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        <td>Bills:internet</td><td>$0</td><td>Not Yet</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        <td>Bills:rent</td><td>-12500</td><td>1990-04-15</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        <td>Fridge</td><td>-1500</td><td>1990-04-26</td>",
            "    </tr>",
            "</table>",
            "<h2>Date: <i>1990-05</i></h2>",
            "<table>",
            "<tr><th>Bills</th><th>Price</th><th>Pay Date</th></tr>",
            "",
            "    <tr>",
            "        <td>Bills:electricity</td><td>$0</td><td>Not Yet</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        "
            "<td>Bills:internet</td><td>-488</td><td>1990-05-25</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        <td>Bills:rent</td><td>$0</td><td>Not Yet</td>",
            "    </tr>",
            "",
            "    <tr>",
            "        <td>Fridge</td><td>$0</td><td>Not Yet</td>",
            "    </tr>",
            "</table>",
            "",
        ]
        got = balance.subp_topay_html(self).split("\n")
        self.assertEqual(got, expect)

    def test_party(self):
        self.assertEqual(balance.subp_party(self), "Success")
        # FIXME - add a "Fail" case too

    def test_csv(self):
        expect = [
            'Value,Date,Comment\r',
            '500,1990-04-03,#dues:test1\r',
            '20,1990-04-03,Unknown\r',
            '-12500,1990-04-15,#bills:rent\r',
            '-1500,1990-04-26,#fridge\r',
            '1500,1990-04-27,#fridge\r',
            '-1174,1990-04-27,#bills:electricity\r',
            '500,1990-05-02,#dues:test1 !locn:test_location\r',
            '0,1990-05-14,!locn_xfer:test_location:test_location2:200\r',
            '-488,1990-05-25,#bills:internet\r',
            '13152,1990-05-25,balance books\r',
            '\r',
            'Sum\r',
            '10\r',
            '',
        ]

        got = balance.subp_csv(self).split("\n")
        self.assertEqual(got, expect)

    def test_grid2(self):
        expect = [
            "                    1990-04  1990-05 ",
            "bills:electricity     -1174         ",
            "bills:internet                  -488",
            "bills:rent           -12500         ",
            "dues:test1              500      500",
            "fridge                    0         ",
            "unknown                  20    13152",
            "",
            "MONTH Sub Total      -13154    13164",
            "RUNNING Balance      -13154       10",
            "TOTAL:     10",
        ]

        self.display_days_prev = None
        self.display_days_post = None
        got = balance.subp_grid(self).split("\n")
        self.assertEqual(got, expect)

    # TODO
    # - test grid output with filter_hack set

    def test_json_payments(self):
        expect = {
            'unknown':    '1990-05',
            'fridge':   '1990-04',
            'dues:test1': '1990-05',
        }
        got = json.loads(balance.subp_json_payments(self))
        self.assertEqual(got, expect)

    @mock.patch('balance.datetime.datetime', fakedatetime)
    def test_make_balance(self):
        got = balance.subp_make_balance(self)

        # this is the {grid_header} values from the template
        want = "        1990-04  1990-05</pre>\n"
        self.assertTrue(want in got)

        # this is the {grid} values from the template
        want = "Test1       500      500</pre>\n"
        self.assertTrue(want in got)

        # this is the {rent_due} value from the template, with some of
        # the template mixed in
        # TODO - have a testable "rowset.forcastNext(category)" function
        want = '(due: <span class="color_neg">1990-04-23</span>) Rent:'
        self.assertTrue(want in got)

        # this is the ${balance_this_month} value from the template
        want = '   <td class="bill_value color_pos">13164&nbsp;HKD</td>'
        self.assertTrue(want in got)

    def test_roundtrip(self):
        got = balance.subp_roundtrip(self)
        self.assertEqual(got, self.input_data)

# TODO
# - test create_stats() independantly
# - add a test with a mocked time that has no members paid (to test the
#   zero divsion avoidance if test in the ARPM generation)

    @mock.patch('balance.datetime.datetime', fakedatetime)
    def test_stats(self):
        # FIXME - this would look more meaningful with at least one more
        #         month's data
        expect = [
            '                 1990-04    Average    MonthTD      Total',
            'outgoing          -15174     -15174       -488     -15174',
            'incoming            2020       2020      13652       2020',
            '',
            ' dues:               500        500        500        500',
            ' other:             1520       1520      13152       1520',
            '',
            'nr members             1          1          1          1',
            'ARPM                 500        500        500        500',
            '',
            'members needed',
            ' dues 500             31         31',
            ' dues 700             22         22',
            'dues needed',
            ' members 1         15174      15174',
            ' members 17          892        892',
            ' members 30          505        505',
            '',
            'Note: Total column does not include MonthTD numbers',
            '',
        ]

        got = balance.subp_stats(self).split("\n")
        self.assertEqual(got, expect)

    @mock.patch('balance.datetime.datetime', fakedatetime)
    def test_statstsv(self):
        expect = [
            '#column 1 timestamp',
            '#column 3 balance',
            '#column 4 subtotal',
            '#column 5 outgoing',
            '#column 6 incoming',
            '#column 7 dues',
            '#column 8 other',
            '#column 9 members',
            '#column 10 ARPM',
            '638928000 1990-04 -13154 -13154 -15174 2020 500 1520 1 500 ',
            '# x Average -26308 -13154 -15174 2020 500 1520 1 500 ',
            '641520000 MonthTD -13144 13164 -488 13652 500 13152 1 500 ',
            '# x Total -26298 -13154 -15174 2020 500 1520 1 500 ',
            '',
        ]

        got = balance.subp_statstsv(self).split("\n")
        self.assertEqual(got, expect)

    def test_subp_check_doubletxn(self):
        self.assertEqual(balance.subp_check_doubletxn(self), None)

        self.rows.append(
            balance.RowData(   "500", Date(1990, 5,12), "#dues:test1 unwanted second payment") # noqa
        )
        with self.assertRaises(ValueError):
            balance.subp_check_doubletxn(self)

    def test_subp_report_location(self):
        expect = [
            'test_location:',
            '500 1990-05-02 #dues:test1 !locn:test_location',
            '-200 1990-05-14 !locn_xfer:test_location:test_location2:200 !locn:test_location', # noqa
            '',
            'test_location2:',
            '200 1990-05-14 !locn_xfer:test_location:test_location2:200 !locn:test_location2', # noqa
            '',
            'unknown:',
            '',
            '#balance 0 Opening Balance',
            '500 1990-04-03 #dues:test1',
            '20 1990-04-03 Unknown',
            '1500 1990-04-27 #fridge',
            '-12500 1990-04-15 #bills:rent',
            '-1174 1990-04-27 #bills:electricity',
            '-1500 1990-04-26 #fridge',
            '-488 1990-05-25 #bills:internet',
            '13152 1990-05-25 balance books',
            '#balance 10 Closing balance',
            '',
            '',
            '',
            '',
            'TOTALS',
            '',
            'test_location 300',
            'test_location2 200',
            'unknown -490',
            '',
        ]

        got = balance.subp_report_location(self).split("\n")
        self.assertEqual(got, expect)
