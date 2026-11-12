from crapper.coverage import CoverageBundle, load_bundle, parse_cobertura
from crapper.languages.csharp import functions_in_source
from crapper.model import Function

SCORE = """
class Board {
    int Score(bool ready) {
        int total = 0;
        for (int i = 0; i < 3; i++) { total++; }
        foreach (int item in items) { total += item; }
        while (ready) { total++; }
        do { total++; } while (ready);
        if (ready && total > 0 || total < 9) { total++; }
        int extra = ready ? 1 : 0;
        try { total++; } catch (Exception error) { total++; }
        return total;
    }
}
"""

NESTED = """
class Board {
    int Score(bool ready) {
        for (int i = 0; i < 3; i++) {
            if (ready) { }
        }
        foreach (int item in items) {
            if (item > 0) { }
        }
        while (ready) {
            if (ready) { }
        }
        do {
            if (ready) { }
        } while (ready);
        int extra = ready ? (open ? 1 : 0) : 2;
        try { } catch (Exception error) {
            if (error != null) { }
        }
        return extra;
    }
}
"""

SWITCHED = """
class Board {
    int Switched(int value) {
        switch (value) {
            case 1:
                if (value > 0) { return 1; }
                break;
            default:
                return 0;
        }
    }
}
"""

LAMBDA = """
class Board {
    int Outer() {
        System.Action runnable = () => { if (true) { } };
        return 1;
    }
}
"""

LOCAL = """
class Board {
    int Local(bool ready) {
        int Nested(bool value) {
            if (value) { return 1; }
            return 0;
        }
        return Nested(ready);
    }
}
"""


def test_decisions_raise_complexity_by_one_each():
    methods = functions_in_source(SCORE, "Sample.cs")
    assert [(method.name, method.complexity) for method in methods] == [("Score", 10)]


def test_nested_decisions_count_and_a_switch_case_counts():
    methods = functions_in_source(NESTED, "Sample.cs")
    switched = functions_in_source(SWITCHED, "Sample.cs")
    assert methods[0].complexity == 13
    assert switched[0].complexity == 4


def test_a_lambda_is_not_its_own_method_and_does_not_raise_the_outer_one():
    methods = functions_in_source(LAMBDA, "Sample.cs")
    assert [method.name for method in methods] == ["Outer"]
    assert methods[0].complexity == 1


def test_a_local_function_is_scored_apart_from_its_enclosing_method():
    methods = functions_in_source(LOCAL, "Sample.cs")
    assert [(method.name, method.complexity) for method in methods] == [
        ("Local", 1),
        ("Nested", 2),
    ]


def test_constructors_are_ignored_and_the_type_name_is_the_namespace():
    source = """
namespace demo.pkg;
class Board {
    Board() { if (true) { } }
    void Place() { return; }
    class Inner {
        void Tick() { return; }
    }
}
"""
    methods = functions_in_source(source, "src/demo/pkg/Board.cs")
    assert [(method.name, method.namespace) for method in methods] == [
        ("Place", "demo.pkg.Board"),
        ("Tick", "demo.pkg.Board.Inner"),
    ]


def test_an_expression_bodied_method_keeps_its_decision():
    source = """
class Board {
    int Place(bool ready) => ready ? 1 : 0;
}
"""
    methods = functions_in_source(source, "Sample.cs")
    assert [(method.name, method.complexity) for method in methods] == [("Place", 2)]


def test_comments_and_strings_are_not_decisions():
    source = """
class Board {
    int Stable() {
        string note = "if for while && || ?";
        return 1; // if (true && false)
    }
}
"""
    first = functions_in_source(source, "Sample.cs")
    second = functions_in_source(source, "Sample.cs")
    assert first[0].complexity == 1
    assert [(method.name, method.complexity) for method in first] == [
        (method.name, method.complexity) for method in second
    ]


def test_coverlet_line_hits_cover_the_method(tmp_path):
    xml = """<?xml version="1.0" ?>
<coverage>
  <packages><package><classes>
    <class filename="src/Board.cs">
      <lines>
        <line number="2" hits="1" />
        <line number="3" hits="0" />
      </lines>
    </class>
  </classes></package></packages>
</coverage>
"""
    (tmp_path / "coverage.cobertura.xml").write_text(xml, encoding="utf-8")
    method = Function(
        name="Place",
        namespace="Board",
        complexity=1,
        start_line=2,
        end_line=3,
        path="src/Board.cs",
        language="csharp",
    )
    assert CoverageBundle(cobertura=parse_cobertura(xml)).percent_for(method) == 50.0
    assert load_bundle(tmp_path).percent_for(method) == 50.0
