<template>
    <div class="person">
        <h2>Name: {{ name }}</h2>
        <h2>Age: {{ age }}</h2>
        <button @click="changeName">Change Name</button>
        <button @click="changeAge">Change Age</button>
        <button @click="showTel">Contact</button>
    </div>
</template>

<script lang="ts">
    export default {
        name: "Person",
        setup() {
            // data
            let name: string = '张三' // 非相应式定义
            let age: number = 18
            let tel: string = '13888888888'

            // methods
            function changeName():void {
                name = 'Zhang San'
                console.log(name) // 数据被修改了，但是页面不会发生变化
            }

            function changeAge():void {
                age += 1
                console.log(age) // 数据被修改了，但是页面不会发生变化
            }

            function showTel():void {
                alert(tel)
            }

            return {name, age, changeName, changeAge, showTel}
        }
    }
</script>

<style scoped>
    .person {
        background-color: skyblue;
        box-shadow: 0 0 10px;
        border-radius: 10px;
        padding: 20px;
    }
    button {
        margin: 0 5px;
    }
</style>