function validateTest() {

    let capacity =
        document.getElementById("capacity").value;

    let testLoad =
        document.getElementById("test_load").value;

    if (parseFloat(testLoad) > parseFloat(capacity)) {

        alert(
            "Test load cannot exceed maximum capacity."
        );

        return false;
    }

    return true;
}