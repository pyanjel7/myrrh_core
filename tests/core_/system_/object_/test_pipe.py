import unittest
import threading

from myrrh.core.services.system import Buffer


class TestBuffer(unittest.TestCase):
    def test_basic_buffer_create(self):
        b = Buffer(threading.RLock(), threading.RLock(), 100)

        self.assertFalse(b.closed)
        self.assertEqual(b.wr_size, 100)

    def test_basic_buffer_write_read(self):
        b = Buffer(threading.RLock(), threading.RLock(), 100)

        b.write(b"01234")
        self.assertEqual(b.rd_size, 5)
        self.assertEqual(b.rd_pos, 0)

        d = b.read()
        self.assertEqual(d, b"01234")
        self.assertEqual(b.rd_pos, 5)
        self.assertEqual(b.rd_size, 0)

        b.write(b"56789")
        self.assertEqual(b.rd_size, 5)
        self.assertEqual(b.rd_pos, 5)

        d = b.read(2)
        self.assertEqual(d, b"56")
        self.assertEqual(b.rd_pos, 7)
        self.assertEqual(b.rd_size, 3)

        d = b.read()
        self.assertEqual(d, b"789")
        self.assertEqual(b.rd_pos, 10)
        self.assertEqual(b.rd_size, 0)

    def test_basic_buffer_n_write_read(self):
        b = Buffer(threading.RLock(), threading.RLock(), 100)

        b.write(b"01234")
        self.assertEqual(b.rd_size, 5)
        self.assertEqual(b.rd_pos, 0)

        b.write(b"56789")
        self.assertEqual(b.rd_size, 10)
        self.assertEqual(b.rd_pos, 0)

        d = b.read()
        self.assertEqual(d, b"0123456789")
        self.assertEqual(b.rd_pos, 10)
        self.assertEqual(b.rd_size, 0)

    def test_basic_rotate(self):
        b = Buffer(threading.RLock(), threading.RLock(), 100)

        for i in range(0, 10):
            prev_rd_pos = b.rd_pos
            prev_wr_pos = b.wr_pos
            b.write(b"0" * 90)
            self.assertEqual(b.rd_pos, prev_rd_pos)
            self.assertEqual(b.wr_pos, (prev_wr_pos + 90) % 100)
            self.assertEqual(b.rd_size, 90)
            self.assertEqual(b.wr_size, 10)

            prev_rd_pos = b.rd_pos
            prev_wr_pos = b.wr_pos
            d = b.read()
            self.assertEqual(d, b"0" * 90)
            self.assertEqual(b.rd_pos, (prev_rd_pos + 90) % 100)
            self.assertEqual(b.wr_pos, prev_wr_pos)
            self.assertEqual(b.rd_size, 0)
            self.assertEqual(b.wr_size, 100)

            prev_rd_pos = b.rd_pos
            prev_wr_pos = b.wr_pos
            b.write(b"1" * 90)
            self.assertEqual(b.rd_pos, prev_rd_pos)
            self.assertEqual(b.wr_pos, (prev_wr_pos + 90) % 100)
            self.assertEqual(b.rd_size, 90)
            self.assertEqual(b.wr_size, 10)

            prev_rd_pos = b.rd_pos
            prev_wr_pos = b.wr_pos
            d = b.read(50)
            self.assertEqual(d, b"1" * 50)
            self.assertEqual(b.rd_pos, (prev_rd_pos + 50) % 100)
            self.assertEqual(b.wr_pos, prev_wr_pos)
            self.assertEqual(b.rd_size, 40)
            self.assertEqual(b.wr_size, 60)

            prev_rd_pos = b.rd_pos
            prev_wr_pos = b.wr_pos
            b.write(b"2" * 20)
            self.assertEqual(b.rd_pos, prev_rd_pos)
            self.assertEqual(b.wr_pos, (prev_wr_pos + 20) % 100)
            self.assertEqual(b.rd_size, 60)
            self.assertEqual(b.wr_size, 40)

            prev_rd_pos = b.rd_pos
            prev_wr_pos = b.wr_pos
            d = b.read(40)
            self.assertEqual(d, b"1" * 40)
            self.assertEqual(b.wr_pos, prev_wr_pos)
            self.assertEqual(b.rd_pos, (prev_rd_pos + 40) % 100)
            self.assertEqual(b.rd_size, 20)
            self.assertEqual(b.wr_size, 80)

            prev_rd_pos = b.rd_pos
            prev_wr_pos = b.wr_pos
            d = b.read()
            self.assertEqual(d, b"2" * 20)
            self.assertEqual(b.rd_pos, (prev_rd_pos + 20) % 100)
            self.assertEqual(b.rd_size, 0)
            self.assertEqual(b.wr_size, 100)

            prev_rd_pos = b.rd_pos
            prev_wr_pos = b.wr_pos
            b.write(b"3" * 30)
            self.assertEqual(b.wr_pos, (prev_wr_pos + 30) % 100)
            self.assertEqual(b.rd_pos, prev_rd_pos)
            self.assertEqual(b.rd_size, 30)
            self.assertEqual(b.wr_size, 70)

            prev_rd_pos = b.rd_pos
            prev_wr_pos = b.wr_pos
            d = b.read()
            self.assertEqual(d, b"3" * 30)
            self.assertEqual(b.wr_pos, prev_wr_pos)
            self.assertEqual(b.rd_pos, (prev_rd_pos + 30) % 100)
            self.assertEqual(b.rd_size, 0)
            self.assertEqual(b.wr_size, 100)


if __name__ == "__main__":
    unittest.main()
