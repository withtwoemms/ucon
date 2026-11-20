# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
"""Operation is part of a formula's identity (#381).

`H = D × w_R` says nothing about `D / w_R`, but the registry keyed its
indexes and its collision guard on the input tuple alone. Two consequences:
a product formula answered a quotient lookup — so `Gy / w_R` claimed to be a
dose equivalent — and the inverse formula ADR 013 §4 names as the way to get a
quotient kind could not be registered at all, because #347's guard read it as
a collision.

`commutative` is a different axis: it governs operand *order within* one
operation.
"""

import pytest

from ucon import Number, units
from ucon.dimension import Dimension
from ucon.formulas import FormulaRegistry, KindFormula
from ucon.formulas.exceptions import CollidingFormula, FormulaNotFound
from ucon.formulas.types import Operation
from ucon.kinds.types import Kind
from ucon.system import active_kinds


@pytest.fixture
def kinds():
    return {
        'dose': Kind(name='dose', dimension=Dimension.specific_energy),
        'wr': Kind(name='wr', dimension=Dimension.none),
        'equiv': Kind(name='equiv', dimension=Dimension.specific_energy),
        'back': Kind(name='back', dimension=Dimension.specific_energy),
        'other': Kind(name='other', dimension=Dimension.specific_energy),
    }


def formula(name, a, b, out, operation=Operation.MULTIPLY):
    return KindFormula(
        name=name,
        expression=f'{a.name} {operation.value} {b.name}',
        input_kinds={'a': a, 'b': b},
        output_kind=out,
        commutative=(operation is Operation.MULTIPLY),
        operation=operation,
    )


class TestOperationIsPartOfTheSignature:
    def test_a_product_and_a_quotient_may_claim_one_input_tuple(self, kinds):
        """Refused as a collision before #381, so the inverse was undeclarable."""
        registry = FormulaRegistry()
        registry.register(formula('weighting', kinds['dose'], kinds['wr'], kinds['equiv']))
        registry.register(formula(
            'unweighting', kinds['dose'], kinds['wr'], kinds['back'], Operation.DIVIDE,
        ))
        assert sorted(f.name for f in registry) == ['unweighting', 'weighting']

    def test_each_answers_only_its_own_operation(self, kinds):
        registry = FormulaRegistry([
            formula('weighting', kinds['dose'], kinds['wr'], kinds['equiv']),
            formula('unweighting', kinds['dose'], kinds['wr'], kinds['back'],
                    Operation.DIVIDE),
        ])
        inputs = {'a': kinds['dose'], 'b': kinds['wr']}
        assert registry.apply(inputs, operation=Operation.MULTIPLY)[1] is kinds['equiv']
        assert registry.apply(inputs, operation=Operation.DIVIDE)[1] is kinds['back']

    def test_a_product_does_not_answer_a_quotient_lookup(self, kinds):
        """The defect itself: one formula, asked the other question."""
        registry = FormulaRegistry([
            formula('weighting', kinds['dose'], kinds['wr'], kinds['equiv']),
        ])
        with pytest.raises(FormulaNotFound):
            registry.apply({'a': kinds['dose'], 'b': kinds['wr']},
                           operation=Operation.DIVIDE)

    def test_multiply_is_the_default(self, kinds):
        """Every formula declared before #381 keeps its behaviour."""
        f = KindFormula(name='f', expression='a * b',
                        input_kinds={'a': kinds['dose'], 'b': kinds['wr']},
                        output_kind=kinds['equiv'])
        assert f.operation is Operation.MULTIPLY
        registry = FormulaRegistry([f])
        assert registry.apply({'a': kinds['dose'], 'b': kinds['wr']})[1] is kinds['equiv']


class TestTheGuardStillGuards:
    """#347's refusal survives, narrowed to one operation at a time."""

    @pytest.mark.parametrize('operation', [Operation.MULTIPLY, Operation.DIVIDE])
    def test_disagreeing_outputs_within_one_operation_refuse(self, kinds, operation):
        registry = FormulaRegistry([
            formula('first', kinds['dose'], kinds['wr'], kinds['equiv'], operation),
        ])
        with pytest.raises(CollidingFormula):
            registry.register(
                formula('second', kinds['dose'], kinds['wr'], kinds['other'], operation)
            )

    def test_the_message_names_the_contested_operation(self, kinds):
        registry = FormulaRegistry([
            formula('first', kinds['dose'], kinds['wr'], kinds['equiv'], Operation.DIVIDE),
        ])
        with pytest.raises(CollidingFormula) as caught:
            registry.register(formula(
                'second', kinds['dose'], kinds['wr'], kinds['other'], Operation.DIVIDE,
            ))
        assert 'dose / wr' in str(caught.value)
        assert caught.value.operation == '/'

    def test_agreeing_outputs_are_still_admitted(self, kinds):
        """One relationship declared twice under two names; first wins."""
        registry = FormulaRegistry([
            formula('first', kinds['dose'], kinds['wr'], kinds['equiv']),
        ])
        registry.register(formula('alias', kinds['dose'], kinds['wr'], kinds['equiv']))
        assert len(registry) == 2


class TestTheShippedCase:
    """`radiation_weighting` is the one formula in the catalog."""

    def test_the_product_still_stamps_dose_equivalent(self):
        lattice = active_kinds()
        dose = Number(2, units.gray, kind=lattice.get('absorbed_dose'))
        w_r = Number(20, units.one, kind=lattice.get('radiation_weighting_factor'))
        assert (dose * w_r).kind.name == 'dose_equivalent'

    def test_the_quotient_no_longer_claims_it(self):
        """Dividing an absorbed dose *by* a weighting factor is not a dose
        equivalent. It answered `<0.1 Gy [dose_equivalent]>` before #381."""
        lattice = active_kinds()
        dose = Number(2, units.gray, kind=lattice.get('absorbed_dose'))
        w_r = Number(20, units.one, kind=lattice.get('radiation_weighting_factor'))
        with pytest.raises(FormulaNotFound):
            dose / w_r


class TestSerialization:
    def test_operation_round_trips(self, kinds):
        from ucon.serialization import _serialize_formula
        div = formula('d', kinds['dose'], kinds['wr'], kinds['back'], Operation.DIVIDE)
        assert _serialize_formula(div)['operation'] == '/'

    def test_the_default_is_omitted(self, kinds):
        from ucon.serialization import _serialize_formula
        mul = formula('m', kinds['dose'], kinds['wr'], kinds['equiv'])
        assert 'operation' not in _serialize_formula(mul)
