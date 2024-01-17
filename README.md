<img src="https://gist.githubusercontent.com/withtwoemms/0cb9e6bc8df08f326771a89eeb790f8e/raw/dde6c7d3b8a7d79eb1006ace03fb834e044cdebc/ucon-logo.png" align="left" width="450" />

# ucon

> Pronounced: _yoo · cahn_

[![tests](https://github.com/withtwoemms/ucon/workflows/tests/badge.svg)](https://github.com/withtwoemms/ucon/actions?query=workflow%3Atests) [![codecov](https://codecov.io/gh/withtwoemms/ucon/graph/badge.svg?token=BNONQTRJWG)](https://codecov.io/gh/withtwoemms/ucon) [![publish](https://github.com/withtwoemms/ucon/workflows/publish/badge.svg)](https://github.com/withtwoemms/ucon/actions?query=workflow%3Apublish)

# Background

Numbers are particularly helpful when describing quantities of some thing (say, 42 ice cream cones 🍦).
They are also useful when describing characteristics of a thing such as it's weight or volume.
Being able to describe a thing by measurements of its defining features and even monitoring said features over time, is foundational to developing an understanding of how the thing works in the world.
"Units" is the general term for those quantifying descriptors that characterize an object.
Specific units include those like [grams](https://en.wikipedia.org/wiki/Gram) for weight, [liter](https://en.wikipedia.org/wiki/Litre) for volume, and even the [jiffy](https://en.wikipedia.org/wiki/Jiffy_(time)) for time.
With means to refer to an object's physical characteristics, their extent can be communicated using a scale to answer the question: _"how many of a given unit accurately describe that aspect of the object?"_.

# Introduction

Since the [metric scale](https://en.wikipedia.org/wiki/Metric_prefix) is fairly ubiquitous and straightfowrward to count with (being base 10 and all..), `ucon` uses the Metric System as the basis for measurement though [binary prefixes](https://en.wikipedia.org/wiki/Binary_prefix) are also supported.
The crux of this tiny library is to provide abstractions that simplify the answering of questions like:

> _"If given two milliliters of bromine (liquid Br<sub>2</sub>), how many grams of bromine does one have?"_

To best answer this question, we turn to an age-old technique ([dimensional analysis](https://en.wikipedia.org/wiki/Dimensional_analysis)) which essentially allows for the solution to be written as a product of ratios.

```
 2 mL bromine | 3.119 g bromine
--------------x-----------------  #=> 6.238 g bromine
      1       |  1 mL bromine
```

# Setup

Ensure `nox` is installed.
```
pip install -r requirements.txt
```
Run `nox -s install` to install `ucon` and `nox -s test` to run tests.

# Usage

The above calculation can be achieved using types defined in the `ucon` module.

```python
two_milliliters_bromine = Number(unit=Units.liter, scale=Scale.milli, quantity=2)
bromine_density = Ratio(numerator=Number(unit=Units.gram, quantity=3.119)
                        denominator=Number(unit=Units.liter, scale=Scale.milli))
two_milliliters_bromine * bromine_density  #=> <6.238 gram>
```

One can also arbitrarily change scale:

```python
answer = two_milliliters_bromine * bromine_density  #=> <6.238 gram>
answer.to(Scale.milli)                              #=> <6238.0 milligram>
answer.to(Scale.kibi)                               #=> <0.006091796875 kibigram>
```
