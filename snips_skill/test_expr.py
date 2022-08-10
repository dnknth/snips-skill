from expr import Parser
import unittest
    
class ExprTest(unittest.TestCase):
    
    parser = Parser()

    def test_less(self):
        expr = self.parser.parse('topic/a < 1')
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertFalse(expr({ 'topic/a' : 1 }))
        self.assertFalse(expr({ 'topic/a' : '1' }))
        self.assertTrue(expr({ 'topic/a' : 0 }))
        self.assertTrue(expr({ 'topic/a' : '0' }))
        self.assertTrue(expr.last_state)
        self.assertRaises(KeyError, expr, {})
        self.assertRaises(ValueError, expr, { 'topic/a' : 'foo' })

    def test_less_equal(self):
        expr = self.parser.parse('topic/a <= 1')
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertFalse(expr({ 'topic/a' : 2 }))
        self.assertFalse(expr({ 'topic/a' : '2' }))
        self.assertTrue(expr({ 'topic/a' : 1 }))
        self.assertTrue(expr({ 'topic/a' : '1' }))
        self.assertTrue(expr.last_state)
        self.assertRaises(KeyError, expr, {})
        self.assertRaises(ValueError, expr, { 'topic/a' : 'foo' })

    def test_greater_equal(self):
        expr = self.parser.parse('topic/a >= 1')
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertFalse(expr({ 'topic/a' : 0 }))
        self.assertFalse(expr({ 'topic/a' : '0' }))
        self.assertTrue(expr({ 'topic/a' : 1 }))
        self.assertTrue(expr({ 'topic/a' : '1' }))
        self.assertTrue(expr.last_state)
        self.assertRaises(KeyError, expr, {})
        self.assertRaises(ValueError, expr, { 'topic/a' : 'foo' })

    def test_greater(self):
        expr = self.parser.parse('topic/a > 1')
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertFalse(expr({ 'topic/a' : 1 }))
        self.assertFalse(expr({ 'topic/a' : '1' }))
        self.assertTrue(expr({ 'topic/a' : 2 }))
        self.assertTrue(expr({ 'topic/a' : '2' }))
        self.assertTrue(expr.last_state)
        self.assertRaises(KeyError, expr, {})
        self.assertRaises(ValueError, expr, { 'topic/a' : 'foo' })

    def test_negative_greater(self):
        expr = self.parser.parse('topic/a > -1')
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertFalse(expr({ 'topic/a' : -1 }))
        self.assertFalse(expr({ 'topic/a' : '-1' }))
        self.assertTrue(expr({ 'topic/a' : 0 }))
        self.assertTrue(expr({ 'topic/a' : '0' }))
        self.assertTrue(expr.last_state)
        self.assertRaises(KeyError, expr, {})
        self.assertRaises(ValueError, expr, { 'topic/a' : 'foo' })

    def test_equal_number(self):
        expr = self.parser.parse('topic/a == 1')
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertFalse(expr({ 'topic/a' : 0 }))
        self.assertFalse(expr({ 'topic/a' : '0' }))
        self.assertTrue(expr({ 'topic/a' : 1 }))
        self.assertTrue(expr({ 'topic/a' : '1' }))
        self.assertTrue(expr.last_state)
        self.assertRaises(KeyError, expr, {})
        self.assertRaises(ValueError, expr, { 'topic/a' : 'foo' })

    def test_equal_string(self):
        expr = self.parser.parse("topic/a == '1'")
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertFalse(expr({ 'topic/a' : '' }))
        self.assertTrue(expr({ 'topic/a' : '1' }))
        self.assertTrue(expr({ 'topic/a' : 1 }))
        self.assertTrue(expr.last_state)
        self.assertRaises(KeyError, expr, {})

    def test_regex_match(self):
        expr = self.parser.parse("topic/a ~= 'o.?o'")
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertTrue(expr({ 'topic/a' : 'zoo' }))
        self.assertTrue(expr({ 'topic/a' : 'bozo' }))
        self.assertFalse(expr({ 'topic/a' : 'bar' }))
        self.assertFalse(expr.last_state)
        self.assertRaises(KeyError, expr, {})

    def test_not_equal_number(self):
        expr = self.parser.parse('topic/a != 1')
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertFalse(expr({ 'topic/a' : 1 }))
        self.assertFalse(expr({ 'topic/a' : '1' }))
        self.assertTrue(expr({ 'topic/a' : 0 }))
        self.assertTrue(expr({ 'topic/a' : '0' }))
        self.assertTrue(expr.last_state)
        self.assertRaises(KeyError, expr, {})
        self.assertRaises(ValueError, expr, { 'topic/a' : 'foo' })

    def test_not_equal_string(self):
        expr = self.parser.parse("topic/a != '1'")
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertFalse(expr({ 'topic/a' : '1' }))
        self.assertTrue(expr({ 'topic/a' : '' }))
        self.assertTrue(expr({ 'topic/a' : 0 }))
        self.assertTrue(expr.last_state)
        self.assertRaises(KeyError, expr, {})

    def test_not(self):
        expr = self.parser.parse("not topic/a == 1")
        self.assertEqual(expr.keys, set(['topic/a']))
        self.assertFalse(expr({ 'topic/a' : 1 }))
        self.assertTrue(expr({ 'topic/a' : 2 }))
        self.assertTrue(expr.last_state)
        self.assertRaises(KeyError, expr, {})

    def test_and(self):
        expr = self.parser.parse("topic/a == 1 and topic/b == 2")
        self.assertEqual(expr.keys, set(['topic/a', 'topic/b']))
        self.assertTrue(expr({ 'topic/a' : 1, 'topic/b' : 2 }))
        self.assertFalse(expr({ 'topic/a' : 0, 'topic/b' : 2 }))
        self.assertFalse(expr({ 'topic/a' : 1, 'topic/b' : 0 }))
        self.assertFalse(expr.last_state)
        self.assertRaises(KeyError, expr, {})

    def test_or(self):
        expr = self.parser.parse("topic/a == 1 or topic/b == 2")
        self.assertEqual(expr.keys, set(['topic/a', 'topic/b']))
        self.assertTrue(expr({ 'topic/a' : 1, 'topic/b' : 1 }))
        self.assertTrue(expr({ 'topic/a' : 0, 'topic/b' : 2 }))
        self.assertFalse(expr({ 'topic/a' : 0, 'topic/b' : 0 }))
        self.assertFalse(expr.last_state)
        self.assertRaises(KeyError, expr, {})

    def test_precedence(self):
        expr = self.parser.parse("topic/b == 1 and topic/a == 2 or topic/a == 3 and topic/b == 4")
        self.assertEqual(expr.keys, set(['topic/a', 'topic/b']))
        self.assertTrue(expr({ 'topic/a' : 2, 'topic/b' : 1 }))
        self.assertTrue(expr({ 'topic/a' : 3, 'topic/b' : 4 }))
        self.assertFalse(expr({ 'topic/a' : 2, 'topic/b' : 3 }))
        self.assertFalse(expr.last_state)

    def test_parenthesis(self):
        expr = self.parser.parse("topic/a == 1 and (topic/b == 2 or topic/b == 3)")
        self.assertEqual(expr.keys, set(['topic/a', 'topic/b']))
        self.assertTrue(expr({ 'topic/a' : 1, 'topic/b' : 2 }))
        self.assertTrue(expr({ 'topic/a' : 1, 'topic/b' : 3 }))
        self.assertTrue(expr.last_state)

if __name__ == '__main__': unittest.main()
