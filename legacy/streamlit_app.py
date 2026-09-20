import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import streamlit as st
import numpy as np
import sympy as sp

from core.fourier.series import (
    calculate_coefficients,
    evaluate_series,
    calculate_absolute_error
)

from core.calculus.parser import parse_function

from core.calculus.calculus import (
    differentiate,
    integrate,
    evaluate,
    parse_expression
)

from core.algebra.linear_algebra import (
    parse_matrix,
    determinant,
    inverse,
    eigenvalues,
    eigenvectors
)

from core.ode.constant_coeff import (
    complementary_function,
    particular_integral_exponential,
    particular_integral_trigonometric,
    particular_integral_polynomial,
    particular_integral_exponential_function,
    build_complete_solution,
    verify_ode_solution
)

from core.ode.first_order import (
    variable_separable,
    linear_differential_equation,
    bernoulli_equation,
    exact_equation
)

from core.pde.first_order import (
    eliminate_arbitrary_constants,
    lagrange_linear_pde,
    standard_type_1,
    standard_type_2_clairaut,
    standard_type_3_separable,
    standard_type_4_no_xy
)

from core.numerical.utils import (
    parse_matrix_text,
    parse_values_text
)

from core.numerical.root_finding import (
    bisection,
    newton_raphson,
    secant
)

from core.numerical.differentiation import (
    forward_difference,
    backward_difference,
    central_difference,
    second_derivative_central
)

from core.numerical.integration import (
    trapezoidal_rule,
    simpsons_one_third_rule,
    simpsons_three_eighth_rule
)

from core.numerical.interpolation import (
    lagrange_interpolation,
    newton_divided_difference
)

from core.numerical.linear_systems import (
    gauss_elimination,
    jacobi_iteration,
    gauss_seidel
)

from core.transforms.laplace import (
    laplace_transform,
    inverse_laplace_transform,
    first_shifting_theorem,
    second_shifting_theorem,
    derivative_property,
    integral_property,
    multiplication_by_t,
    division_by_t
)

from core.transforms.fourier_transform import (
    fourier_transform,
    inverse_fourier_transform,
    fourier_sine_transform,
    inverse_fourier_sine_transform,
    fourier_cosine_transform,
    inverse_fourier_cosine_transform,
    shifting_property as fourier_shifting_property,
    scaling_property as fourier_scaling_property
)

from core.transforms.z_transform import (
    z_transform,
    inverse_z_transform,
    linearity_property as z_linearity_property,
    scaling_theorem as z_scaling_theorem,
    time_shifting_theorem as z_time_shifting_theorem,
    initial_value_theorem as z_initial_value_theorem,
    final_value_theorem as z_final_value_theorem
)


from visualization.plots import create_fourier_plot


def format_decimal(value, places=3):
    """
    Round a number to a fixed number of decimal places
    for display, avoiding both long float noise and a
    stray "-0.000" for tiny negative-near-zero values.
    """

    rounded = round(value, places)

    if rounded == 0:
        rounded = 0.0

    return f"{rounded:.{places}f}"


st.set_page_config(
    page_title="MathNova",
    page_icon="∑",
    layout="wide"
)


st.title("∑ MathNova")
st.subheader("Mathematical Analysis & Simulation Engine")

st.markdown("---")


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

st.sidebar.title("MathNova")

module = st.sidebar.selectbox(
    "Select Module",
    [
        "Fourier Series",
        "Calculus",
        "Linear Algebra",
        "ODE",
        "PDE",
        "Numerical Methods",
        "Transforms"
    ]
)


# =========================================================
# FOURIER SERIES
# =========================================================

if module == "Fourier Series":

    st.header("Fourier Series")

    st.write(
        "Calculate and visualize the Fourier series "
        "approximation of a mathematical function."
    )

    st.subheader("Fourier Series Calculator")

    col1, col2 = st.columns(2)

    with col1:

        function_name = st.text_input(
            "Function f(x)",
            value="x"
        )

    with col2:

        L = st.number_input(
            "Half Period L",
            value=float(np.pi),
            min_value=0.1
        )

    N = st.slider(
        "Number of Fourier Terms",
        min_value=1,
        max_value=100,
        value=10
    )

    calculate = st.button(
        "Calculate Fourier Series",
        type="primary"
    )

    if calculate:

        try:

            function = parse_function(
                function_name
            )

            a0, an, bn = calculate_coefficients(
                function,
                L,
                N
            )

            st.markdown("---")

            st.subheader("Fourier Coefficients")

            st.latex(
                f"a_0 = {a0:.10f}"
            )

            coefficient_data = []

            for n in range(1, N + 1):

                coefficient_data.append(
                    {
                        "n": n,
                        "aₙ": an[n - 1],
                        "bₙ": bn[n - 1]
                    }
                )

            st.dataframe(
                coefficient_data,
                use_container_width=True
            )

            # -------------------------------------------------
            # APPROXIMATION
            # -------------------------------------------------

            x_value = L / 2

            actual = function(
                x_value
            )

            approximation = evaluate_series(
                x_value,
                L,
                a0,
                an,
                bn
            )

            error = calculate_absolute_error(
                actual,
                approximation
            )

            st.markdown("---")

            st.subheader("Visualization")

            figure = create_fourier_plot(
                function,
                L,
                a0,
                an,
                bn
            )

            st.plotly_chart(
                figure,
                use_container_width=True
            )

            st.markdown("---")

            st.subheader("Approximation")

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "x",
                    f"{x_value:.8f}"
                )

            with col2:

                st.metric(
                    "Actual f(x)",
                    f"{float(actual):.8f}"
                )

            with col3:

                st.metric(
                    "Fourier Approximation",
                    f"{float(approximation):.8f}"
                )

            st.metric(
                "Absolute Error",
                f"{float(error):.8f}"
            )

        except Exception as error:

            st.error(
                f"Invalid mathematical expression: {error}"
            )


# =========================================================
# CALCULUS
# =========================================================

elif module == "Calculus":

    st.header("Calculus Engine")

    st.write(
        "Perform symbolic differentiation, "
        "integration, and function evaluation."
    )

    expression = st.text_input(
        "Enter mathematical expression",
        value="x^3 + 2*x"
    )

    evaluation_point = st.number_input(
        "Evaluate at x =",
        value=2.0
    )

    calculate = st.button(
        "Calculate",
        type="primary"
    )

    if calculate:

        try:

            derivative = differentiate(
                expression
            )

            integral = integrate(
                expression
            )

            value = evaluate(
                expression,
                evaluation_point
            )

            st.subheader("Results")

            col1, col2, col3 = st.columns(3)

            with col1:

                st.write("**f(x)**")

                st.latex(
                    sp.latex(
                        parse_expression(expression)
                    )
                )

            with col2:

                st.write("**Derivative**")

                st.latex(
                    sp.latex(derivative)
                )

            with col3:

                st.write(
                    f"**f({evaluation_point})**"
                )

                st.latex(
                    f"{float(value):.6f}"
                )

            st.subheader(
                "Indefinite Integral"
            )

            st.latex(
                f"\\int "
                f"({sp.latex(parse_expression(expression))})"
                f"\\,dx"
                f"="
                f"{sp.latex(integral)} + C"
            )

        except Exception as error:

            st.error(
                f"Invalid mathematical expression: {error}"
            )


# =========================================================
# LINEAR ALGEBRA
# =========================================================

elif module == "Linear Algebra":

    st.header("Linear Algebra Engine")

    st.write(
        "Analyze matrices using determinants, inverses, "
        "eigenvalues, and eigenvectors."
    )

    matrix_text = st.text_area(
        "Enter matrix",
        value="2, 1\n1, 2",
        height=120
    )

    calculate_matrix = st.button(
        "Calculate Matrix",
        type="primary"
    )

    if calculate_matrix:

        try:

            matrix = parse_matrix(
                matrix_text
            )

            st.subheader("Matrix")

            st.latex(
                sp.latex(matrix)
            )

            st.markdown("---")

            # -------------------------------------------------
            # DETERMINANT
            # -------------------------------------------------

            st.subheader("Determinant")

            det = determinant(
                matrix
            )

            st.latex(
                f"\\det(A) = {sp.latex(det)}"
            )

            # -------------------------------------------------
            # INVERSE
            # -------------------------------------------------

            st.subheader("Inverse")

            try:

                matrix_inverse = inverse(
                    matrix
                )

                st.latex(
                    f"A^{{-1}} = "
                    f"{sp.latex(matrix_inverse)}"
                )

            except Exception:

                st.warning(
                    "This matrix does not have an inverse."
                )

            # -------------------------------------------------
            # EIGENVALUES
            # -------------------------------------------------

            st.subheader("Eigenvalues")

            try:

                values = eigenvalues(
                    matrix
                )

                for eigenvalue, multiplicity in values.items():

                    st.latex(
                        f"\\lambda = "
                        f"{sp.latex(eigenvalue)}"
                        f"\\quad "
                        f"(multiplicity = {multiplicity})"
                    )

            except Exception:

                st.warning(
                    "Eigenvalues require a square matrix."
                )

            # -------------------------------------------------
            # EIGENVECTORS
            # -------------------------------------------------

            st.subheader("Eigenvectors")

            try:

                vectors = eigenvectors(
                    matrix
                )

                for eigenvalue, multiplicity, vector_list in vectors:

                    st.latex(
                        f"\\lambda = "
                        f"{sp.latex(eigenvalue)}"
                    )

                    for vector in vector_list:

                        st.latex(
                            f"v = {sp.latex(vector)}"
                        )

            except Exception:

                st.warning(
                    "Eigenvectors require a square matrix."
                )

        except Exception as error:

            st.error(
                f"Invalid matrix: {error}"
            )


# =========================================================
# ODE
# =========================================================

elif module == "ODE":

    st.header("Ordinary Differential Equations")

    st.write(
        "Solve ordinary differential equations using "
        "engineering mathematics methods."
    )

    ode_type = st.selectbox(
        "Select ODE Method",
        [
            "Complementary Function",
            "Particular Integral",
            "Complete Solution",
            "First Order ODE"
        ]
    )

    # -----------------------------------------------------
    # COMPLEMENTARY FUNCTION
    # -----------------------------------------------------

    if ode_type == "Complementary Function":

        st.subheader(
            "Complementary Function"
        )

        st.write(
            "Find the Complementary Function using the "
            "auxiliary equation."
        )

        st.latex(
            r"F(D)y = 0"
        )

        st.write(
            "Enter the coefficients of the differential "
            "operator in descending powers of D."
        )

        st.caption(
            "Example: D² − 3D + 2 → 1, -3, 2"
        )

        coefficient_text = st.text_input(
            "Coefficients",
            value="1, -3, 2"
        )

        calculate_cf = st.button(
            "Calculate Complementary Function",
            type="primary"
        )

        if calculate_cf:

            try:

                coefficient_values = []

                for value in coefficient_text.split(","):

                    coefficient_values.append(
                        sp.sympify(
                            value.strip()
                        )
                    )

                if len(coefficient_values) < 2:

                    raise ValueError(
                        "At least two coefficients are required."
                    )

                auxiliary_equation, roots, cf = (
                    complementary_function(
                        coefficient_values
                    )
                )

                st.markdown("---")

                st.subheader(
                    "Auxiliary Equation"
                )

                st.latex(
                    sp.latex(
                        auxiliary_equation
                    )
                )

                st.subheader(
                    "Characteristic Roots"
                )

                for root, multiplicity in roots.items():

                    if multiplicity == 1:

                        st.latex(
                            f"m = {sp.latex(root)}"
                        )

                    else:

                        st.latex(
                            f"m = {sp.latex(root)}"
                            f"\\quad "
                            f"(multiplicity = {multiplicity})"
                        )

                st.subheader(
                    "Complementary Function"
                )

                st.latex(
                    sp.latex(cf)
                )

            except Exception as error:

                st.error(
                    f"Invalid ODE coefficients: {error}"
                )


# -----------------------------------------------------
# PARTICULAR INTEGRAL
# -----------------------------------------------------

    elif ode_type == "Particular Integral":

        st.subheader(
            "Particular Integral"
        )

        st.latex(
            r"PI = \frac{1}{F(D)}X"
        )

        st.markdown(
            "Calculate the Particular Integral using "
            "standard engineering mathematics methods."
        )

        # -----------------------------
        # Operator
        # -----------------------------

        st.markdown("### Differential Operator")

        coefficients_text = st.text_input(
            "Enter operator coefficients",
            value="1,-3,2",
            help=(
                "For D² - 3D + 2 enter: "
                "1,-3,2"
            ),
            key="pi_coefficients"
        )

        try:
            coefficients = [
                sp.sympify(value.strip())
                for value in coefficients_text.split(",")
                if value.strip()
            ]

            if len(coefficients) < 2:
                raise ValueError(
                    "Enter at least two coefficients."
                )

        except Exception as error:

            st.error(
                f"Invalid coefficients: {error}"
            )

            st.stop()

        st.divider()

        # -----------------------------
        # PI Type
        # -----------------------------

        pi_type = st.selectbox(
            "Select Forcing Function",
            [
                "Exponential",
                "Sine",
                "Cosine",
                "Polynomial",
                "Exponential × Function"
            ],
            key="pi_type"
        )

        st.divider()

        # -----------------------------
        # Exponential
        # -----------------------------

        if pi_type == "Exponential":

            a = st.number_input(
                "Enter a",
                value=4.0,
                step=1.0
            )

            if st.button(
                "Calculate PI",
                key="pi_exponential"
            ):

                try:

                    result = (
                        particular_integral_exponential(
                            coefficients,
                            a
                        )
                    )

                    st.markdown("### Results")

                    st.latex(
                        r"F(D) = "
                        + sp.latex(result["operator"])
                    )

                    st.write(
                        "F(a):",
                        result["F_a"]
                    )

                    if result["resonance"]:

                        st.warning(
                            "Resonance detected."
                        )

                        st.write(
                            "Multiplicity:",
                            result["multiplicity"]
                        )

                    else:

                        st.success(
                            "Non-resonant case"
                        )

                    st.markdown("### Particular Integral")

                    st.latex(
                        r"PI = "
                        + sp.latex(result["pi"])
                    )

                except Exception as error:

                    st.error(
                        f"Unable to calculate PI: {error}"
                    )

        # -----------------------------
        # Sine
        # -----------------------------

        elif pi_type == "Sine":

            a = st.number_input(
                "Enter a",
                value=2.0,
                step=1.0
            )

            if st.button(
                "Calculate PI",
                key="pi_sine"
            ):

                try:

                    result = (
                        particular_integral_trigonometric(
                            coefficients,
                            a,
                            "sin"
                        )
                    )

                    st.markdown("### Results")

                    st.latex(
                        r"F(D) = "
                        + sp.latex(result["operator"])
                    )

                    st.latex(
                        r"F(ia) = "
                        + sp.latex(result["F_ia"])
                    )

                    st.markdown(
                        "### Particular Integral"
                    )

                    st.latex(
                        r"PI = "
                        + sp.latex(result["pi"])
                    )

                except Exception as error:

                    st.error(
                        f"Unable to calculate PI: {error}"
                    )

        # -----------------------------
        # Cosine
        # -----------------------------

        elif pi_type == "Cosine":

            a = st.number_input(
                "Enter a",
                value=2.0,
                step=1.0
            )

            if st.button(
                "Calculate PI",
                key="pi_cosine"
            ):

                try:

                    result = (
                        particular_integral_trigonometric(
                            coefficients,
                            a,
                            "cos"
                        )
                    )

                    st.markdown("### Results")

                    st.latex(
                        r"F(D) = "
                        + sp.latex(result["operator"])
                    )

                    st.latex(
                        r"F(ia) = "
                        + sp.latex(result["F_ia"])
                    )

                    st.markdown(
                        "### Particular Integral"
                    )

                    st.latex(
                        r"PI = "
                        + sp.latex(result["pi"])
                    )

                except Exception as error:

                    st.error(
                        f"Unable to calculate PI: {error}"
                    )

        # -----------------------------
        # Polynomial
        # -----------------------------

        elif pi_type == "Polynomial":

            forcing = st.text_input(
                "Enter polynomial X(x)",
                value="x^2"
            )

            if st.button(
                "Calculate PI",
                key="pi_polynomial"
            ):

                try:

                    result = (
                        particular_integral_polynomial(
                            coefficients,
                            forcing
                        )
                    )

                    st.markdown("### Results")

                    st.latex(
                        r"F(D) = "
                        + sp.latex(
                            result["original_operator"]
                        )
                    )

                    st.latex(
                        r"X(x) = "
                        + sp.latex(
                            result["forcing"]
                        )
                    )

                    st.write(
                        "Polynomial Degree:",
                        result["degree"]
                    )

                    st.markdown(
                        "### Particular Integral"
                    )

                    st.latex(
                        r"PI = "
                        + sp.latex(result["pi"])
                    )

                except Exception as error:

                    st.error(
                        f"Unable to calculate PI: {error}"
                    )

        # -----------------------------
        # Exponential × Function
        # -----------------------------

        elif pi_type == "Exponential × Function":

            a = st.number_input(
                "Enter a",
                value=4.0,
                step=1.0
            )

            function = st.text_input(
                "Enter V(x)",
                value="x^2"
            )

            st.latex(
                r"RHS = e^{ax}V(x)"
            )

            if st.button(
                "Calculate PI",
                key="pi_exponential_function"
            ):

                try:

                    result = (
                        particular_integral_exponential_function(
                            coefficients,
                            a,
                            function
                        )
                    )

                    st.markdown("### Results")

                    st.latex(
                        r"F(D) = "
                        + sp.latex(result["operator"])
                    )

                    st.latex(
                        r"F(D+a) = "
                        + sp.latex(
                            result["shifted_operator"]
                        )
                    )

                    st.latex(
                        r"V(x) = "
                        + sp.latex(
                            result["forcing_function"]
                        )
                    )

                    st.markdown(
                        "### Polynomial PI"
                    )

                    st.latex(
                        sp.latex(
                            result["polynomial_pi"]
                        )
                    )

                    st.markdown(
                        "### Particular Integral"
                    )

                    st.latex(
                        r"PI = "
                        + sp.latex(result["pi"])
                    )

                except Exception as error:

                    st.error(
                        f"Unable to calculate PI: {error}"
                    )


    # -----------------------------------------------------
    # COMPLETE SOLUTION
    # -----------------------------------------------------

    elif ode_type == "Complete Solution":

        st.subheader(
            "Complete Solution"
        )

        st.latex(
            r"\boxed{y = CF + PI}"
        )

        st.markdown(
            "Solve the non-homogeneous constant-coefficient "
            "ODE using the Complementary Function and "
            "Particular Integral."
        )

        st.divider()

        # -----------------------------
        # Differential Operator
        # -----------------------------

        st.markdown(
            "### Differential Operator"
        )

        coefficients_text = st.text_input(
            "Enter operator coefficients",
            value="1,-3,2",
            help=(
                "For D² - 3D + 2 enter: "
                "1,-3,2"
            ),
            key="complete_coefficients"
        )

        try:

            coefficients = [
                sp.sympify(value.strip())
                for value in coefficients_text.split(",")
                if value.strip()
            ]

            if len(coefficients) < 2:
                raise ValueError(
                    "Enter at least two coefficients."
                )

        except Exception as error:

            st.error(
                f"Invalid coefficients: {error}"
            )

            st.stop()

        st.divider()

        # -----------------------------
        # Forcing Function
        # -----------------------------

        pi_type = st.selectbox(
            "Select RHS / Forcing Function",
            [
                "Exponential",
                "Sine",
                "Cosine",
                "Polynomial",
                "Exponential × Function"
            ],
            key="complete_pi_type"
        )

        a = None
        function = None
        forcing = None

        # -----------------------------
        # Exponential
        # -----------------------------

        if pi_type == "Exponential":

            a = st.number_input(
                "Enter a",
                value=4.0,
                step=1.0,
                key="complete_exp_a"
            )

            a = sp.Rational(str(a))

            forcing = f"exp({sp.latex(a)}*x)"

        # -----------------------------
        # Sine
        # -----------------------------

        elif pi_type == "Sine":

            a = st.number_input(
                "Enter a",
                value=2.0,
                step=1.0,
                key="complete_sine_a"
            )

            a = sp.Rational(str(a))

            forcing = f"sin({a}*x)"

        # -----------------------------
        # Cosine
        # -----------------------------

        elif pi_type == "Cosine":

            a = st.number_input(
                "Enter a",
                value=2.0,
                step=1.0,
                key="complete_cosine_a"
            )

            a = sp.Rational(str(a))

            forcing = f"cos({a}*x)"

        # -----------------------------
        # Polynomial
        # -----------------------------

        elif pi_type == "Polynomial":

            function = st.text_input(
                "Enter X(x)",
                value="x^2",
                key="complete_polynomial"
            )

            forcing = function

        # -----------------------------
        # Exponential × Function
        # -----------------------------

        elif pi_type == "Exponential × Function":

            a = st.number_input(
                "Enter a",
                value=4.0,
                step=1.0,
                key="complete_exp_function_a"
            )

            a = sp.Rational(str(a))

            function = st.text_input(
                "Enter V(x)",
                value="x^2",
                key="complete_exp_function"
            )

            forcing = (
                f"exp({a}*x)*({function})"
            )

        st.divider()

        if st.button(
            "Solve Complete ODE",
            type="primary",
            key="solve_complete_ode"
        ):

            try:

                # =============================
                # CF
                # =============================

                auxiliary_equation, roots, cf = (
                    complementary_function(
                        coefficients
                    )
                )

                # =============================
                # PI
                # =============================

                if pi_type == "Exponential":

                    pi_result = (
                        particular_integral_exponential(
                            coefficients,
                            a
                        )
                    )

                elif pi_type == "Sine":

                    pi_result = (
                        particular_integral_trigonometric(
                            coefficients,
                            a,
                            "sin"
                        )
                    )

                elif pi_type == "Cosine":

                    pi_result = (
                        particular_integral_trigonometric(
                            coefficients,
                            a,
                            "cos"
                        )
                    )

                elif pi_type == "Polynomial":

                    pi_result = (
                        particular_integral_polynomial(
                            coefficients,
                            function
                        )
                    )

                else:

                    pi_result = (
                        particular_integral_exponential_function(
                            coefficients,
                            a,
                            function
                        )
                    )

                pi = pi_result["pi"]

                # =============================
                # COMPLETE SOLUTION
                # =============================

                result = build_complete_solution(
                    coefficients,
                    cf,
                    pi,
                    forcing
                )

                # =============================
                # DISPLAY
                # =============================

                st.success(
                    "ODE solved successfully."
                )

                st.markdown(
                    "## 1. Auxiliary Equation"
                )

                st.latex(
                    sp.latex(auxiliary_equation)
                )

                st.markdown(
                    "## 2. Roots"
                )

                for root, multiplicity in roots.items():

                    if multiplicity == 1:

                        st.latex(
                            rf"m = {sp.latex(root)}"
                        )

                    else:

                        st.latex(
                            rf"m = {sp.latex(root)}"
                            rf"\quad \text{{multiplicity}} = {multiplicity}"
                        )

                st.markdown(
                    "## 3. Complementary Function"
                )

                cf_display = sp.simplify(
                    result["cf"]
                )

                st.latex(
                    rf"CF = {sp.latex(cf_display)}"
                )

                st.markdown(
                    "## 4. Particular Integral"
                )

                pi_display = sp.factor(
                    sp.nsimplify(result["pi"])
                )   
                st.latex(
                    rf"PI = {sp.latex(pi_display)}"
                )

                st.markdown(
                    "## 5. Complete Solution"
                )

                complete_solution = sp.factor(
                    sp.nsimplify(
                        result["complete_solution"]
                    )
                )

                st.latex(
                    rf"\boxed{{{sp.latex(complete_solution)}}}"
                )

                # =============================
                # VERIFICATION
                # =============================

                st.divider()

                st.markdown(
                    "## 6. Verification"
                )

                cf_verified = (
                    result[
                        "cf_verification"
                    ]["verified"]
                )

                pi_verified = (
                    result[
                        "pi_verification"
                    ]["verified"]
                )

                complete_verified = (
                    result[
                        "complete_verification"
                    ]["verified"]
                )

                if cf_verified:
                    st.success(
                        "✓ CF Verified: F(D)(CF) = 0"
                    )
                else:
                    st.error(
                        "✗ CF Verification Failed"
                    )

                if pi_verified:
                    st.success(
                        "✓ PI Verified: F(D)(PI) = RHS"
                    )
                else:
                    st.error(
                        "✗ PI Verification Failed"
                    )

                if complete_verified:
                    st.success(
                        "✓ Complete Solution Verified"
                    )
                else:
                    st.error(
                        "✗ Complete Solution Verification Failed"
                    )

                with st.expander(
                    "Show verification details"
                ):

                    st.write(
                        "CF Difference:",
                        result[
                            "cf_verification"
                        ]["difference"]
                    )

                    st.write(
                        "PI Difference:",
                        result[
                            "pi_verification"
                        ]["difference"]
                    )

                    st.write(
                        "Complete Difference:",
                        result[
                            "complete_verification"
                        ]["difference"]
                    )

            except Exception as error:

                st.error(
                    f"Unable to solve ODE: {error}"
                )

    # -----------------------------------------------------
    # FIRST ORDER ODE
    # -----------------------------------------------------

    elif ode_type == "First Order ODE":

        st.subheader(
            "First Order Differential Equation"
        )

        method_type = st.selectbox(
            "Select Method",
            [
                "Variable Separable",
                "Linear Differential Equation",
                "Bernoulli's Equation",
                "Exact Differential Equation"
            ],
            key="first_order_method"
        )

        st.divider()

        # -----------------------------
        # Variable Separable
        # -----------------------------

        if method_type == "Variable Separable":

            st.latex(
                r"\frac{dy}{dx} = f(x)\,g(y)"
            )

            f_x_text = st.text_input(
                "Enter f(x)",
                value="x",
                key="separable_fx"
            )

            g_y_text = st.text_input(
                "Enter g(y)",
                value="y",
                key="separable_gy"
            )

            if st.button(
                "Solve",
                type="primary",
                key="solve_separable"
            ):

                try:

                    result = variable_separable(
                        f_x_text,
                        g_y_text
                    )

                    st.markdown("### Solution")

                    st.latex(
                        sp.latex(result["solution"])
                    )

                    if result["verified"]:
                        st.success(
                            "✓ Verified: dy/dx = f(x) g(y)"
                        )
                    else:
                        st.warning(
                            "Could not verify the solution "
                            "automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to solve: {error}"
                    )

        # -----------------------------
        # Linear Differential Equation
        # -----------------------------

        elif method_type == "Linear Differential Equation":

            st.latex(
                r"\frac{dy}{dx} + P(x)y = Q(x)"
            )

            P_text = st.text_input(
                "Enter P(x)",
                value="1/x",
                key="linear_p"
            )

            Q_text = st.text_input(
                "Enter Q(x)",
                value="x^2",
                key="linear_q"
            )

            if st.button(
                "Solve",
                type="primary",
                key="solve_linear"
            ):

                try:

                    result = linear_differential_equation(
                        P_text,
                        Q_text
                    )

                    st.markdown(
                        "### Integrating Factor"
                    )

                    st.latex(
                        r"IF = "
                        + sp.latex(
                            result["integrating_factor"]
                        )
                    )

                    st.markdown("### Solution")

                    st.latex(
                        sp.latex(result["solution"])
                    )

                    if result["verified"]:
                        st.success(
                            "✓ Verified: dy/dx + P(x)y = Q(x)"
                        )
                    else:
                        st.warning(
                            "Could not verify the solution "
                            "automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to solve: {error}"
                    )

        # -----------------------------
        # Bernoulli's Equation
        # -----------------------------

        elif method_type == "Bernoulli's Equation":

            st.latex(
                r"\frac{dy}{dx} + P(x)y = Q(x)y^n"
            )

            P_text = st.text_input(
                "Enter P(x)",
                value="1/x",
                key="bernoulli_p"
            )

            Q_text = st.text_input(
                "Enter Q(x)",
                value="x^2",
                key="bernoulli_q"
            )

            n_value = st.number_input(
                "Enter n",
                value=2.0,
                step=1.0,
                key="bernoulli_n"
            )

            if st.button(
                "Solve",
                type="primary",
                key="solve_bernoulli"
            ):

                try:

                    n_rational = sp.Rational(
                        str(n_value)
                    )

                    result = bernoulli_equation(
                        P_text,
                        Q_text,
                        n_rational
                    )

                    st.markdown("### Substitution")

                    st.latex(
                        r"v = y^{1-n}"
                    )

                    st.markdown("### Solution")

                    st.latex(
                        sp.latex(result["solution"])
                    )

                    if result["verified"]:
                        st.success(
                            "✓ Verified: "
                            "dy/dx + P(x)y = Q(x)y^n"
                        )
                    else:
                        st.warning(
                            "Could not verify the solution "
                            "automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to solve: {error}"
                    )

        # -----------------------------
        # Exact Differential Equation
        # -----------------------------

        elif method_type == "Exact Differential Equation":

            st.latex(
                r"M(x,y)\,dx + N(x,y)\,dy = 0"
            )

            M_text = st.text_input(
                "Enter M(x, y)",
                value="2*x*y + y^2",
                key="exact_m"
            )

            N_text = st.text_input(
                "Enter N(x, y)",
                value="x^2 + 2*x*y",
                key="exact_n"
            )

            if st.button(
                "Solve",
                type="primary",
                key="solve_exact"
            ):

                try:

                    result = exact_equation(
                        M_text,
                        N_text
                    )

                    st.markdown(
                        "### Exactness Check"
                    )

                    st.latex(
                        r"\partial M/\partial y = "
                        + sp.latex(result["dM_dy"])
                    )

                    st.latex(
                        r"\partial N/\partial x = "
                        + sp.latex(result["dN_dx"])
                    )

                    st.success(
                        "Equation is exact."
                    )

                    st.markdown("### Solution")

                    st.latex(
                        sp.latex(result["solution"])
                    )

                    if result["verified"]:
                        st.success(
                            "✓ Verified: dy/dx = -M/N"
                        )
                    else:
                        st.warning(
                            "Could not verify the solution "
                            "automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to solve: {error}"
                    )


# =========================================================
# PDE
# =========================================================

elif module == "PDE":

    st.header("Partial Differential Equations")

    st.write(
        "Solve first-order partial differential equations "
        "using engineering mathematics methods."
    )

    pde_type = st.selectbox(
        "Select PDE Method",
        [
            "Formation of PDE",
            "Lagrange's Linear PDE",
            "Standard Type I",
            "Standard Type II (Clairaut)",
            "Standard Type III (Separable)",
            "Standard Type IV (z, p, q only)"
        ]
    )

    st.divider()

    # -----------------------------------------------------
    # FORMATION OF PDE
    # -----------------------------------------------------

    if pde_type == "Formation of PDE":

        st.subheader("Formation of PDE")

        st.latex(
            r"z = f(x, y;\ \text{arbitrary constants})"
        )

        st.write(
            "Eliminate one or two arbitrary constants "
            "from z = f(x, y) to form the corresponding "
            "first-order PDE."
        )

        z_text = st.text_input(
            "Enter z = f(x, y)",
            value="a*x + a^2*y^2 + b",
            key="pde_form_z"
        )

        constants_text = st.text_input(
            "Enter arbitrary constants (comma separated)",
            value="a, b",
            key="pde_form_constants"
        )

        if st.button(
            "Form PDE",
            type="primary",
            key="pde_form_button"
        ):

            try:

                constants = [
                    name.strip()
                    for name in constants_text.split(",")
                    if name.strip()
                ]

                result = eliminate_arbitrary_constants(
                    z_text,
                    constants
                )

                st.markdown("### Derived PDE")

                st.latex(
                    sp.latex(result["pde"])
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified: elimination checks "
                        "out identically."
                    )
                else:
                    st.warning(
                        "Could not verify the elimination "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to form PDE: {error}"
                )

    # -----------------------------------------------------
    # LAGRANGE'S LINEAR PDE
    # -----------------------------------------------------

    elif pde_type == "Lagrange's Linear PDE":

        st.subheader("Lagrange's Linear PDE")

        st.latex(
            r"Pp + Qq = R"
        )

        st.write(
            "Solve using the subsidiary equations "
            "dx/P = dy/Q = dz/R."
        )

        P_text = st.text_input(
            "Enter P(x, y, z)",
            value="y*z",
            key="lagrange_p"
        )

        Q_text = st.text_input(
            "Enter Q(x, y, z)",
            value="x*z",
            key="lagrange_q"
        )

        R_text = st.text_input(
            "Enter R(x, y, z)",
            value="x*y",
            key="lagrange_r"
        )

        if st.button(
            "Solve",
            type="primary",
            key="lagrange_solve"
        ):

            try:

                result = lagrange_linear_pde(
                    P_text,
                    Q_text,
                    R_text
                )

                st.markdown("### First Invariant")

                st.latex(
                    r"u = " + sp.latex(result["u"])
                )

                st.markdown("### Second Invariant")

                st.latex(
                    r"v = " + sp.latex(result["v"])
                )

                st.markdown("### General Solution")

                st.latex(
                    sp.latex(result["general_solution"])
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified: both invariants are "
                        "constant along the characteristics."
                    )
                else:
                    st.warning(
                        "Could not verify one or both "
                        "invariants automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to solve: {error}"
                )

    # -----------------------------------------------------
    # STANDARD TYPE I
    # -----------------------------------------------------

    elif pde_type == "Standard Type I":

        st.subheader(
            "Standard Type I: f(p, q) = 0"
        )

        st.latex(
            r"f(p, q) = 0"
        )

        f_text = st.text_input(
            "Enter f(p, q)",
            value="p*q - 1",
            key="type1_f"
        )

        if st.button(
            "Solve",
            type="primary",
            key="type1_solve"
        ):

            try:

                result = standard_type_1(f_text)

                st.markdown("### Complete Integral")

                st.latex(
                    sp.latex(result["complete_integral"])
                )

                if result["verified"]:
                    st.success("✓ Verified")
                else:
                    st.warning(
                        "Could not verify the solution "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to solve: {error}"
                )

    # -----------------------------------------------------
    # STANDARD TYPE II (CLAIRAUT)
    # -----------------------------------------------------

    elif pde_type == "Standard Type II (Clairaut)":

        st.subheader(
            "Standard Type II: Clairaut's Equation"
        )

        st.latex(
            r"z = px + qy + f(p, q)"
        )

        f_text = st.text_input(
            "Enter f(p, q)",
            value="p*q",
            key="type2_f"
        )

        if st.button(
            "Solve",
            type="primary",
            key="type2_solve"
        ):

            try:

                result = standard_type_2_clairaut(f_text)

                st.markdown("### Complete Integral")

                st.latex(
                    sp.latex(result["complete_integral"])
                )

                if result["verified"]:
                    st.success("✓ Verified")
                else:
                    st.warning(
                        "Could not verify the solution "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to solve: {error}"
                )

    # -----------------------------------------------------
    # STANDARD TYPE III (SEPARABLE)
    # -----------------------------------------------------

    elif pde_type == "Standard Type III (Separable)":

        st.subheader(
            "Standard Type III: f(x, p) = g(y, q)"
        )

        st.latex(
            r"f(x, p) = g(y, q)"
        )

        f_text = st.text_input(
            "Enter f(x, p)",
            value="p^2 - x",
            key="type3_f"
        )

        g_text = st.text_input(
            "Enter g(y, q)",
            value="q - y^2",
            key="type3_g"
        )

        if st.button(
            "Solve",
            type="primary",
            key="type3_solve"
        ):

            try:

                result = standard_type_3_separable(
                    f_text,
                    g_text
                )

                st.markdown("### Complete Integral")

                st.latex(
                    sp.latex(result["complete_integral"])
                )

                if result["verified"]:
                    st.success("✓ Verified")
                else:
                    st.warning(
                        "Could not verify the solution "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to solve: {error}"
                )

    # -----------------------------------------------------
    # STANDARD TYPE IV (x, y ABSENT)
    # -----------------------------------------------------

    elif pde_type == "Standard Type IV (z, p, q only)":

        st.subheader(
            "Standard Type IV: f(z, p, q) = 0"
        )

        st.latex(
            r"f(z, p, q) = 0"
        )

        f_text = st.text_input(
            "Enter f(z, p, q)",
            value="p*q - z",
            key="type4_f"
        )

        if st.button(
            "Solve",
            type="primary",
            key="type4_solve"
        ):

            try:

                result = standard_type_4_no_xy(f_text)

                st.markdown("### Complete Integral")

                st.latex(
                    sp.latex(result["complete_integral"])
                )

                if result["verified"]:
                    st.success("✓ Verified")
                else:
                    st.warning(
                        "Could not verify the solution "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to solve: {error}"
                )


# =========================================================
# NUMERICAL METHODS
# =========================================================

elif module == "Numerical Methods":

    st.header("Numerical Methods")

    st.write(
        "Solve equations, differentiate, integrate, "
        "interpolate, and solve linear systems "
        "numerically."
    )

    numerical_type = st.selectbox(
        "Select Method Category",
        [
            "Bisection Method",
            "Newton-Raphson Method",
            "Secant Method",
            "Numerical Differentiation",
            "Numerical Integration",
            "Interpolation",
            "Linear Systems"
        ]
    )

    st.divider()

    # -----------------------------------------------------
    # BISECTION METHOD
    # -----------------------------------------------------

    if numerical_type == "Bisection Method":

        st.subheader("Bisection Method")

        function_text = st.text_input(
            "Enter f(x)",
            value="x^3 - x - 2",
            key="bisection_f"
        )

        col_a, col_b = st.columns(2)

        with col_a:
            a_value = st.number_input(
                "a",
                value=1.0,
                key="bisection_a"
            )

        with col_b:
            b_value = st.number_input(
                "b",
                value=2.0,
                key="bisection_b"
            )

        tolerance = st.number_input(
            "Tolerance",
            value=1e-6,
            format="%.8f",
            key="bisection_tol"
        )

        if st.button(
            "Solve",
            type="primary",
            key="bisection_solve"
        ):

            try:

                result = bisection(
                    function_text,
                    a_value,
                    b_value,
                    tolerance=tolerance
                )

                st.markdown("### Root")

                st.latex(
                    f"x \\approx {result['root']:.8f}"
                )

                st.write(
                    "Residual f(root): "
                    f"`{format_decimal(result['residual'])}`"
                )

                st.markdown("### Iterations")

                st.dataframe(
                    result["iterations"],
                    use_container_width=True
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified against SymPy's "
                        "nsolve()."
                    )
                else:
                    st.warning(
                        "Could not verify the root "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to solve: {error}"
                )

    # -----------------------------------------------------
    # NEWTON-RAPHSON METHOD
    # -----------------------------------------------------

    elif numerical_type == "Newton-Raphson Method":

        st.subheader("Newton-Raphson Method")

        st.latex(
            r"x_{n+1} = x_n - \frac{f(x_n)}{f'(x_n)}"
        )

        function_text = st.text_input(
            "Enter f(x)",
            value="x^3 - x - 2",
            key="newton_f"
        )

        initial_guess = st.number_input(
            "Initial guess",
            value=1.5,
            key="newton_x0"
        )

        tolerance = st.number_input(
            "Tolerance",
            value=1e-6,
            format="%.8f",
            key="newton_tol"
        )

        if st.button(
            "Solve",
            type="primary",
            key="newton_solve"
        ):

            try:

                result = newton_raphson(
                    function_text,
                    initial_guess,
                    tolerance=tolerance
                )

                st.markdown("### Root")

                st.latex(
                    f"x \\approx {result['root']:.8f}"
                )

                st.write(
                    "Residual f(root): "
                    f"`{format_decimal(result['residual'])}`"
                )

                st.markdown("### Iterations")

                st.dataframe(
                    result["iterations"],
                    use_container_width=True
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified against SymPy's "
                        "nsolve()."
                    )
                else:
                    st.warning(
                        "Could not verify the root "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to solve: {error}"
                )

    # -----------------------------------------------------
    # SECANT METHOD
    # -----------------------------------------------------

    elif numerical_type == "Secant Method":

        st.subheader("Secant Method")

        function_text = st.text_input(
            "Enter f(x)",
            value="x^3 - x - 2",
            key="secant_f"
        )

        col_a, col_b = st.columns(2)

        with col_a:
            x0_value = st.number_input(
                "x0",
                value=1.0,
                key="secant_x0"
            )

        with col_b:
            x1_value = st.number_input(
                "x1",
                value=2.0,
                key="secant_x1"
            )

        tolerance = st.number_input(
            "Tolerance",
            value=1e-6,
            format="%.8f",
            key="secant_tol"
        )

        if st.button(
            "Solve",
            type="primary",
            key="secant_solve"
        ):

            try:

                result = secant(
                    function_text,
                    x0_value,
                    x1_value,
                    tolerance=tolerance
                )

                st.markdown("### Root")

                st.latex(
                    f"x \\approx {result['root']:.8f}"
                )

                st.write(
                    "Residual f(root): "
                    f"`{format_decimal(result['residual'])}`"
                )

                st.markdown("### Iterations")

                st.dataframe(
                    result["iterations"],
                    use_container_width=True
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified against SymPy's "
                        "nsolve()."
                    )
                else:
                    st.warning(
                        "Could not verify the root "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to solve: {error}"
                )

    # -----------------------------------------------------
    # NUMERICAL DIFFERENTIATION
    # -----------------------------------------------------

    elif numerical_type == "Numerical Differentiation":

        st.subheader("Numerical Differentiation")

        diff_type = st.selectbox(
            "Select Formula",
            [
                "Forward Difference",
                "Backward Difference",
                "Central Difference",
                "Second Derivative (Central)"
            ],
            key="diff_type"
        )

        function_text = st.text_input(
            "Enter f(x)",
            value="x^3 - x - 2",
            key="diff_f"
        )

        x0_value = st.number_input(
            "x0",
            value=2.0,
            key="diff_x0"
        )

        h_value = st.number_input(
            "Step size h",
            value=1e-5,
            format="%.8f",
            key="diff_h"
        )

        if st.button(
            "Calculate",
            type="primary",
            key="diff_solve"
        ):

            try:

                if diff_type == "Forward Difference":
                    result = forward_difference(
                        function_text, x0_value, h_value
                    )
                    approx_key = "approx_derivative"
                    exact_key = "exact_derivative"

                elif diff_type == "Backward Difference":
                    result = backward_difference(
                        function_text, x0_value, h_value
                    )
                    approx_key = "approx_derivative"
                    exact_key = "exact_derivative"

                elif diff_type == "Central Difference":
                    result = central_difference(
                        function_text, x0_value, h_value
                    )
                    approx_key = "approx_derivative"
                    exact_key = "exact_derivative"

                else:
                    result = second_derivative_central(
                        function_text, x0_value, h_value
                    )
                    approx_key = "approx_second_derivative"
                    exact_key = "exact_second_derivative"

                st.markdown("### Result")

                st.write(
                    "Approximate: "
                    f"`{format_decimal(result[approx_key])}`"
                )

                st.write(
                    "Exact (symbolic): "
                    f"`{format_decimal(result[exact_key])}`"
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified against the exact "
                        "symbolic derivative."
                    )
                else:
                    st.warning(
                        "Approximation deviates from the "
                        "exact derivative more than "
                        "expected."
                    )

            except Exception as error:

                st.error(
                    f"Unable to calculate: {error}"
                )

    # -----------------------------------------------------
    # NUMERICAL INTEGRATION
    # -----------------------------------------------------

    elif numerical_type == "Numerical Integration":

        st.subheader("Numerical Integration")

        integration_type = st.selectbox(
            "Select Rule",
            [
                "Trapezoidal Rule",
                "Simpson's 1/3 Rule",
                "Simpson's 3/8 Rule"
            ],
            key="integration_type"
        )

        function_text = st.text_input(
            "Enter f(x)",
            value="x^3 - x - 2",
            key="integration_f"
        )

        col_a, col_b = st.columns(2)

        with col_a:
            a_value = st.number_input(
                "a",
                value=0.0,
                key="integration_a"
            )

        with col_b:
            b_value = st.number_input(
                "b",
                value=1.0,
                key="integration_b"
            )

        default_n = (
            10 if integration_type != "Simpson's 3/8 Rule"
            else 9
        )

        n_value = st.number_input(
            "n (subintervals)",
            value=default_n,
            step=1,
            key=f"integration_n_{integration_type}"
        )

        if st.button(
            "Calculate",
            type="primary",
            key="integration_solve"
        ):

            try:

                n_int = int(n_value)

                if integration_type == "Trapezoidal Rule":
                    result = trapezoidal_rule(
                        function_text, a_value, b_value, n_int
                    )

                elif integration_type == "Simpson's 1/3 Rule":
                    result = simpsons_one_third_rule(
                        function_text, a_value, b_value, n_int
                    )

                else:
                    result = simpsons_three_eighth_rule(
                        function_text, a_value, b_value, n_int
                    )

                st.markdown("### Result")

                st.write(
                    "Approximate Integral: "
                    f"`{format_decimal(result['integral'])}`"
                )

                st.write(
                    "Exact (symbolic): "
                    f"`{format_decimal(result['exact_integral'])}`"
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified against the exact "
                        "symbolic integral."
                    )
                else:
                    st.warning(
                        "Approximation deviates from the "
                        "exact integral more than "
                        "expected."
                    )

            except Exception as error:

                st.error(
                    f"Unable to calculate: {error}"
                )

    # -----------------------------------------------------
    # INTERPOLATION
    # -----------------------------------------------------

    elif numerical_type == "Interpolation":

        st.subheader("Interpolation")

        interpolation_type = st.selectbox(
            "Select Method",
            [
                "Lagrange Interpolation",
                "Newton's Divided Difference"
            ],
            key="interpolation_type"
        )

        x_values_text = st.text_input(
            "Enter x values (comma separated)",
            value="0, 1, 2, 3",
            key="interp_x"
        )

        y_values_text = st.text_input(
            "Enter y values (comma separated)",
            value="1, 2, 9, 28",
            key="interp_y"
        )

        x_eval_text = st.text_input(
            "Evaluate polynomial at x (optional)",
            value="1.5",
            key="interp_eval"
        )

        if st.button(
            "Interpolate",
            type="primary",
            key="interp_solve"
        ):

            try:

                x_values = parse_values_text(
                    x_values_text
                )

                y_values = parse_values_text(
                    y_values_text
                )

                x_eval = (
                    float(x_eval_text)
                    if x_eval_text.strip()
                    else None
                )

                if interpolation_type == (
                    "Lagrange Interpolation"
                ):
                    result = lagrange_interpolation(
                        x_values, y_values, x_eval
                    )

                else:
                    result = newton_divided_difference(
                        x_values, y_values, x_eval
                    )

                st.markdown("### Interpolating Polynomial")

                st.latex(
                    "P(x) = " + sp.latex(result["polynomial"])
                )

                if x_eval is not None:
                    st.write(
                        f"P({x_eval}) = "
                        f"`{format_decimal(result['y_eval'])}`"
                    )

                if result["verified"]:
                    st.success(
                        "✓ Verified: passes through all "
                        "given data points."
                    )
                else:
                    st.warning(
                        "Could not verify the polynomial "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to interpolate: {error}"
                )

    # -----------------------------------------------------
    # LINEAR SYSTEMS
    # -----------------------------------------------------

    elif numerical_type == "Linear Systems":

        st.subheader("Linear Systems")

        linear_system_type = st.selectbox(
            "Select Method",
            [
                "Gauss Elimination",
                "Jacobi Iteration",
                "Gauss-Seidel Iteration"
            ],
            key="linear_system_type"
        )

        matrix_text = st.text_area(
            "Enter coefficient matrix A",
            value="4, 1, 2\n3, 5, 1\n1, 1, 3",
            height=120,
            key="linear_system_a"
        )

        vector_text = st.text_input(
            "Enter vector b (comma separated)",
            value="4, 7, 3",
            key="linear_system_b"
        )

        if st.button(
            "Solve",
            type="primary",
            key="linear_system_solve"
        ):

            try:

                matrix_a = parse_matrix_text(
                    matrix_text
                )

                vector_b = parse_values_text(
                    vector_text
                )

                if linear_system_type == (
                    "Gauss Elimination"
                ):
                    result = gauss_elimination(
                        matrix_a, vector_b
                    )

                elif linear_system_type == (
                    "Jacobi Iteration"
                ):
                    result = jacobi_iteration(
                        matrix_a, vector_b
                    )

                else:
                    result = gauss_seidel(
                        matrix_a, vector_b
                    )

                st.markdown("### Solution")

                st.write([
                    round(value, 3)
                    for value in result["solution"]
                ])

                if "iterations" in result:
                    st.markdown("### Iterations")

                    st.dataframe(
                        result["iterations"],
                        use_container_width=True
                    )

                if result["verified"]:
                    st.success(
                        "✓ Verified against "
                        "numpy.linalg.solve()."
                    )
                else:
                    st.warning(
                        "Could not verify the solution "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to solve: {error}"
                )


# =========================================================
# TRANSFORMS
# =========================================================

elif module == "Transforms":

    st.header("Transforms")

    st.write(
        "Laplace, Fourier, and Z-Transforms with their "
        "standard properties and shifting rules."
    )

    transform_type = st.selectbox(
        "Select Transform Category",
        [
            "Laplace Transform",
            "Inverse Laplace Transform",
            "Laplace Properties",
            "Fourier Transform",
            "Fourier Properties",
            "Z-Transform",
            "Inverse Z-Transform",
            "Z-Transform Properties"
        ]
    )

    st.divider()

    # -----------------------------------------------------
    # LAPLACE TRANSFORM
    # -----------------------------------------------------

    if transform_type == "Laplace Transform":

        st.subheader("Laplace Transform")

        st.latex(
            r"F(s) = \int_0^{\infty} f(t)\,e^{-st}\,dt"
        )

        function_text = st.text_input(
            "Enter f(t)",
            value="sin(t)",
            key="laplace_f"
        )

        if st.button(
            "Compute",
            type="primary",
            key="laplace_solve"
        ):

            try:

                result = laplace_transform(function_text)

                st.markdown("### Result")

                st.latex(
                    r"F(s) = " + sp.latex(result["F"])
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified: inverse transform "
                        "recovers f(t)."
                    )
                else:
                    st.warning(
                        "Could not verify the transform "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to compute: {error}"
                )

    # -----------------------------------------------------
    # INVERSE LAPLACE TRANSFORM
    # -----------------------------------------------------

    elif transform_type == "Inverse Laplace Transform":

        st.subheader("Inverse Laplace Transform")

        st.latex(
            r"f(t) = \mathcal{L}^{-1}\{F(s)\}"
        )

        function_text = st.text_input(
            "Enter F(s)",
            value="1/(s^2+1)",
            key="inv_laplace_F"
        )

        if st.button(
            "Compute",
            type="primary",
            key="inv_laplace_solve"
        ):

            try:

                result = inverse_laplace_transform(
                    function_text
                )

                st.markdown("### Result")

                st.latex(
                    r"f(t) = " + sp.latex(result["f"])
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified: forward transform "
                        "recovers F(s)."
                    )
                else:
                    st.warning(
                        "Could not verify the transform "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to compute: {error}"
                )

    # -----------------------------------------------------
    # LAPLACE PROPERTIES
    # -----------------------------------------------------

    elif transform_type == "Laplace Properties":

        st.subheader("Laplace Transform Properties")

        laplace_property_type = st.selectbox(
            "Select Property",
            [
                "First Shifting Theorem",
                "Second Shifting Theorem",
                "Derivative Property",
                "Integral Property",
                "Multiplication by t^n",
                "Division by t"
            ],
            key="laplace_property_type"
        )

        st.divider()

        if laplace_property_type == "First Shifting Theorem":

            st.latex(
                r"\mathcal{L}\{e^{at}f(t)\} = F(s - a)"
            )

            function_text = st.text_input(
                "Enter f(t)",
                value="sin(t)",
                key="first_shift_f"
            )

            a_value = st.number_input(
                "Enter a",
                value=3.0,
                key="first_shift_a"
            )

            if st.button(
                "Compute",
                type="primary",
                key="first_shift_solve"
            ):

                try:

                    result = first_shifting_theorem(
                        function_text, a_value
                    )

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["direct_transform"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "theorem automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif laplace_property_type == "Second Shifting Theorem":

            st.latex(
                r"\mathcal{L}\{f(t-a)u(t-a)\} = "
                r"e^{-as}F(s)"
            )

            function_text = st.text_input(
                "Enter f(t)",
                value="t^2",
                key="second_shift_f"
            )

            a_value = st.number_input(
                "Enter a",
                value=2.0,
                key="second_shift_a"
            )

            if st.button(
                "Compute",
                type="primary",
                key="second_shift_solve"
            ):

                try:

                    result = second_shifting_theorem(
                        function_text, a_value
                    )

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["theorem_result"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "theorem automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif laplace_property_type == "Derivative Property":

            function_text = st.text_input(
                "Enter f(t)",
                value="sin(t)",
                key="derivative_prop_f"
            )

            order = st.selectbox(
                "Order",
                [1, 2],
                key="derivative_prop_order"
            )

            if st.button(
                "Compute",
                type="primary",
                key="derivative_prop_solve"
            ):

                try:

                    result = derivative_property(
                        function_text, order=order
                    )

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["theorem_result"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif laplace_property_type == "Integral Property":

            st.latex(
                r"\mathcal{L}\left\{\int_0^t f(\tau)\,"
                r"d\tau\right\} = \frac{F(s)}{s}"
            )

            function_text = st.text_input(
                "Enter f(t)",
                value="sin(t)",
                key="integral_prop_f"
            )

            if st.button(
                "Compute",
                type="primary",
                key="integral_prop_solve"
            ):

                try:

                    result = integral_property(
                        function_text
                    )

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["theorem_result"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif laplace_property_type == "Multiplication by t^n":

            st.latex(
                r"\mathcal{L}\{t^n f(t)\} = "
                r"(-1)^n F^{(n)}(s)"
            )

            function_text = st.text_input(
                "Enter f(t)",
                value="exp(-2*t)",
                key="mult_t_f"
            )

            power = st.number_input(
                "Enter n",
                value=2,
                step=1,
                key="mult_t_power"
            )

            if st.button(
                "Compute",
                type="primary",
                key="mult_t_solve"
            ):

                try:

                    result = multiplication_by_t(
                        function_text, power=int(power)
                    )

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["theorem_result"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif laplace_property_type == "Division by t":

            st.latex(
                r"\mathcal{L}\left\{\frac{f(t)}{t}"
                r"\right\} = \int_s^{\infty} F(\sigma)"
                r"\,d\sigma"
            )

            function_text = st.text_input(
                "Enter f(t)",
                value="sin(t)",
                key="div_t_f"
            )

            if st.button(
                "Compute",
                type="primary",
                key="div_t_solve"
            ):

                try:

                    result = division_by_t(function_text)

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["theorem_result"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

    # -----------------------------------------------------
    # FOURIER TRANSFORM
    # -----------------------------------------------------

    elif transform_type == "Fourier Transform":

        st.subheader("Fourier Transform")

        fourier_method = st.selectbox(
            "Select Method",
            [
                "Complex Fourier Transform",
                "Inverse Complex Fourier Transform",
                "Fourier Sine Transform",
                "Inverse Fourier Sine Transform",
                "Fourier Cosine Transform",
                "Inverse Fourier Cosine Transform"
            ],
            key="fourier_method"
        )

        st.divider()

        if fourier_method == "Complex Fourier Transform":

            st.latex(
                r"F(w) = \frac{1}{\sqrt{2\pi}}"
                r"\int_{-\infty}^{\infty} f(x)\,"
                r"e^{iwx}\,dx"
            )

            function_text = st.text_input(
                "Enter f(x)",
                value="exp(-x^2)",
                key="fourier_f"
            )

            if st.button(
                "Compute",
                type="primary",
                key="fourier_solve"
            ):

                try:

                    result = fourier_transform(
                        function_text
                    )

                    st.markdown("### Result")

                    st.latex(
                        r"F(w) = " + sp.latex(result["F"])
                    )

                    if result["verified"]:
                        st.success(
                            "✓ Verified: inverse "
                            "transform recovers f(x)."
                        )
                    else:
                        st.warning(
                            "Could not verify the "
                            "transform automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif fourier_method == (
            "Inverse Complex Fourier Transform"
        ):

            function_text = st.text_input(
                "Enter F(w)",
                value="sqrt(2)*exp(-w^2/4)/2",
                key="inv_fourier_F"
            )

            if st.button(
                "Compute",
                type="primary",
                key="inv_fourier_solve"
            ):

                try:

                    result = inverse_fourier_transform(
                        function_text
                    )

                    st.markdown("### Result")

                    st.latex(
                        r"f(x) = " + sp.latex(result["f"])
                    )

                    if result["verified"]:
                        st.success(
                            "✓ Verified: forward "
                            "transform recovers F(w)."
                        )
                    else:
                        st.warning(
                            "Could not verify the "
                            "transform automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif fourier_method == "Fourier Sine Transform":

            st.latex(
                r"F_s(w) = \sqrt{\frac{2}{\pi}}"
                r"\int_0^{\infty} f(x)\sin(wx)\,dx"
            )

            function_text = st.text_input(
                "Enter f(x), x > 0",
                value="exp(-2*x)",
                key="fourier_sine_f"
            )

            if st.button(
                "Compute",
                type="primary",
                key="fourier_sine_solve"
            ):

                try:

                    result = fourier_sine_transform(
                        function_text
                    )

                    st.markdown("### Result")

                    st.latex(
                        r"F_s(w) = " + sp.latex(result["Fs"])
                    )

                    if result["verified"]:
                        st.success(
                            "✓ Verified: self-reciprocal "
                            "round trip recovers f(x)."
                        )
                    else:
                        st.warning(
                            "Could not verify the "
                            "transform automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif fourier_method == (
            "Inverse Fourier Sine Transform"
        ):

            function_text = st.text_input(
                "Enter Fs(w)",
                value="sqrt(2)*w/(sqrt(pi)*(w^2+4))",
                key="inv_fourier_sine_F"
            )

            if st.button(
                "Compute",
                type="primary",
                key="inv_fourier_sine_solve"
            ):

                try:

                    result = inverse_fourier_sine_transform(
                        function_text
                    )

                    st.markdown("### Result")

                    st.latex(
                        r"f(x) = " + sp.latex(result["f"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "transform automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif fourier_method == "Fourier Cosine Transform":

            st.latex(
                r"F_c(w) = \sqrt{\frac{2}{\pi}}"
                r"\int_0^{\infty} f(x)\cos(wx)\,dx"
            )

            function_text = st.text_input(
                "Enter f(x), x > 0",
                value="exp(-2*x)",
                key="fourier_cosine_f"
            )

            if st.button(
                "Compute",
                type="primary",
                key="fourier_cosine_solve"
            ):

                try:

                    result = fourier_cosine_transform(
                        function_text
                    )

                    st.markdown("### Result")

                    st.latex(
                        r"F_c(w) = " + sp.latex(result["Fc"])
                    )

                    if result["verified"]:
                        st.success(
                            "✓ Verified: self-reciprocal "
                            "round trip recovers f(x)."
                        )
                    else:
                        st.warning(
                            "Could not verify the "
                            "transform automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif fourier_method == (
            "Inverse Fourier Cosine Transform"
        ):

            function_text = st.text_input(
                "Enter Fc(w)",
                value="2*sqrt(2)/(sqrt(pi)*(w^2+4))",
                key="inv_fourier_cosine_F"
            )

            if st.button(
                "Compute",
                type="primary",
                key="inv_fourier_cosine_solve"
            ):

                try:

                    result = (
                        inverse_fourier_cosine_transform(
                            function_text
                        )
                    )

                    st.markdown("### Result")

                    st.latex(
                        r"f(x) = " + sp.latex(result["f"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "transform automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

    # -----------------------------------------------------
    # FOURIER PROPERTIES
    # -----------------------------------------------------

    elif transform_type == "Fourier Properties":

        st.subheader("Fourier Transform Properties")

        fourier_property_type = st.selectbox(
            "Select Property",
            [
                "Shifting Property",
                "Scaling Property"
            ],
            key="fourier_property_type"
        )

        st.divider()

        if fourier_property_type == "Shifting Property":

            st.latex(
                r"\mathcal{F}\{f(x-a)\} = e^{iwa}F(w)"
            )

            function_text = st.text_input(
                "Enter f(x)",
                value="exp(-x^2)",
                key="fourier_shift_f"
            )

            a_value = st.number_input(
                "Enter a",
                value=1.0,
                key="fourier_shift_a"
            )

            if st.button(
                "Compute",
                type="primary",
                key="fourier_shift_solve"
            ):

                try:

                    result = fourier_shifting_property(
                        function_text, a_value
                    )

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["theorem_result"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif fourier_property_type == "Scaling Property":

            st.latex(
                r"\mathcal{F}\{f(ax)\} = "
                r"\frac{1}{|a|}F\left(\frac{w}{a}\right)"
            )

            function_text = st.text_input(
                "Enter f(x)",
                value="exp(-x^2)",
                key="fourier_scale_f"
            )

            a_value = st.number_input(
                "Enter a",
                value=2.0,
                key="fourier_scale_a"
            )

            if st.button(
                "Compute",
                type="primary",
                key="fourier_scale_solve"
            ):

                try:

                    result = fourier_scaling_property(
                        function_text, a_value
                    )

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["theorem_result"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

    # -----------------------------------------------------
    # Z-TRANSFORM
    # -----------------------------------------------------

    elif transform_type == "Z-Transform":

        st.subheader("Z-Transform")

        st.latex(
            r"X(z) = \sum_{n=0}^{\infty} x(n)\,z^{-n}"
        )

        sequence_text = st.text_input(
            "Enter x(n)",
            value="a^n",
            key="z_transform_x"
        )

        if st.button(
            "Compute",
            type="primary",
            key="z_transform_solve"
        ):

            try:

                result = z_transform(sequence_text)

                st.markdown("### Result")

                st.latex(
                    r"X(z) = " + sp.latex(result["X"])
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified against a Laurent "
                        "series expansion."
                    )
                else:
                    st.warning(
                        "Could not verify the transform "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to compute: {error}"
                )

    # -----------------------------------------------------
    # INVERSE Z-TRANSFORM
    # -----------------------------------------------------

    elif transform_type == "Inverse Z-Transform":

        st.subheader("Inverse Z-Transform")

        function_text = st.text_input(
            "Enter X(z)",
            value="z/((z-1)*(z-2))",
            key="inv_z_transform_X"
        )

        if st.button(
            "Compute",
            type="primary",
            key="inv_z_transform_solve"
        ):

            try:

                result = inverse_z_transform(
                    function_text
                )

                st.markdown("### Result")

                st.latex(
                    r"x(n) = " + sp.latex(result["x_n"])
                )

                if result["verified"]:
                    st.success(
                        "✓ Verified: forward transform "
                        "recovers X(z)."
                    )
                else:
                    st.warning(
                        "Could not verify the transform "
                        "automatically."
                    )

            except Exception as error:

                st.error(
                    f"Unable to compute: {error}"
                )

    # -----------------------------------------------------
    # Z-TRANSFORM PROPERTIES
    # -----------------------------------------------------

    elif transform_type == "Z-Transform Properties":

        st.subheader("Z-Transform Properties")

        z_property_type = st.selectbox(
            "Select Property",
            [
                "Linearity",
                "Scaling Theorem",
                "Time Shifting Theorem",
                "Initial Value Theorem",
                "Final Value Theorem"
            ],
            key="z_property_type"
        )

        st.divider()

        if z_property_type == "Linearity":

            st.latex(
                r"Z\{a\,x_1(n) + b\,x_2(n)\} = "
                r"aX_1(z) + bX_2(z)"
            )

            x1_text = st.text_input(
                "Enter x1(n)",
                value="a**n",
                key="z_lin_x1"
            )

            x2_text = st.text_input(
                "Enter x2(n)",
                value="b**n",
                key="z_lin_x2"
            )

            col_a, col_b = st.columns(2)

            with col_a:
                a_value = st.number_input(
                    "Enter a",
                    value=2.0,
                    key="z_lin_a"
                )

            with col_b:
                b_value = st.number_input(
                    "Enter b",
                    value=3.0,
                    key="z_lin_b"
                )

            if st.button(
                "Compute",
                type="primary",
                key="z_lin_solve"
            ):

                try:

                    result = z_linearity_property(
                        x1_text, x2_text, a_value, b_value
                    )

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["theorem_result"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif z_property_type == "Scaling Theorem":

            st.latex(
                r"Z\{a^n x(n)\} = X\left(\frac{z}{a}"
                r"\right)"
            )

            sequence_text = st.text_input(
                "Enter x(n)",
                value="n",
                key="z_scale_x"
            )

            a_value = st.number_input(
                "Enter a",
                value=3.0,
                key="z_scale_a"
            )

            if st.button(
                "Compute",
                type="primary",
                key="z_scale_solve"
            ):

                try:

                    result = z_scaling_theorem(
                        sequence_text, a_value
                    )

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["theorem_result"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif z_property_type == "Time Shifting Theorem":

            st.latex(
                r"Z\{x(n-k)\} = z^{-k}X(z)"
            )

            sequence_text = st.text_input(
                "Enter x(n)",
                value="a**n",
                key="z_shift_x"
            )

            k_value = st.number_input(
                "Enter k",
                value=2,
                step=1,
                key="z_shift_k"
            )

            if st.button(
                "Compute",
                type="primary",
                key="z_shift_solve"
            ):

                try:

                    result = z_time_shifting_theorem(
                        sequence_text, int(k_value)
                    )

                    st.markdown("### Result")

                    st.latex(
                        sp.latex(result["theorem_result"])
                    )

                    if result["verified"] is True:
                        st.success("✓ Verified")
                    elif result["verified"] is False:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )
                    else:
                        st.info(
                            "Verification was not "
                            "attempted for this sequence."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif z_property_type == "Initial Value Theorem":

            st.latex(
                r"x(0) = \lim_{z \to \infty} X(z)"
            )

            function_text = st.text_input(
                "Enter X(z)",
                value="z/(z-2)",
                key="z_initial_X"
            )

            if st.button(
                "Compute",
                type="primary",
                key="z_initial_solve"
            ):

                try:

                    result = z_initial_value_theorem(
                        function_text
                    )

                    st.markdown("### Result")

                    st.latex(
                        r"x(0) = "
                        + sp.latex(result["initial_value"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )

        elif z_property_type == "Final Value Theorem":

            st.latex(
                r"\lim_{n \to \infty} x(n) = "
                r"\lim_{z \to 1} (z-1)X(z)"
            )

            function_text = st.text_input(
                "Enter X(z)",
                value="z/(z-0.5)",
                key="z_final_X"
            )

            if st.button(
                "Compute",
                type="primary",
                key="z_final_solve"
            ):

                try:

                    result = z_final_value_theorem(
                        function_text
                    )

                    st.markdown("### Result")

                    st.latex(
                        r"\lim_{n \to \infty} x(n) = "
                        + sp.latex(result["final_value"])
                    )

                    if result["verified"]:
                        st.success("✓ Verified")
                    else:
                        st.warning(
                            "Could not verify the "
                            "property automatically."
                        )

                except Exception as error:

                    st.error(
                        f"Unable to compute: {error}"
                    )


# =========================================================
# OTHER MODULES
# =========================================================

else:

    st.info(
        f"{module} module is coming soon."
    )